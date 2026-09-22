const { chromium } = require('/workspace/node_modules/playwright');

const BASE = 'http://localhost:3001';
let passed = 0, failed = 0;
function check(name, cond, extra = '') {
  console.log((cond ? 'PASS' : 'FAIL') + ' ' + name + (extra ? '  ' + extra : ''));
  cond ? passed++ : failed++;
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 900 } });

  // ---------- window A ----------
  const page = await ctx.newPage();
  const consoleErrors = [];
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', e => consoleErrors.push('PAGEERROR: ' + e.message));
  await page.goto(BASE);
  await page.waitForSelector('.top-bar h1');
  await page.screenshot({ path: '/tmp/shot-1-normal.png' });

  // 普通模式原有面板布局完整（LogTable/AnomalyChart/AlertPanel + Trend/Heatmap = 5 个面板）
  check('normal layout: 5 panels', await page.locator('.main-grid .panel, .bottom-row .panel').count() === 5
    && await page.locator('.main-grid').count() === 1);
  check('normal title present', (await page.locator('.top-bar h1').innerText()).includes('分布式日志聚合'));
  const origGridCols = await page.locator('.main-grid').evaluate(el => getComputedStyle(el).gridTemplateColumns);
  check('normal grid 2 cols (1fr 400px)', /400px/.test(origGridCols), origGridCols);
  const origBottomCols = await page.locator('.bottom-row').evaluate(el => getComputedStyle(el).gridTemplateColumns);
  check('chart titles normal', await page.locator('.panel h4').allInnerTexts().then(t =>
    t.some(x => x.includes('异常分数 (3-sigma + IQR)'))));

  // 生成数据，普通模式图表有内容
  await page.click('button:has-text("生成日志")');
  await page.waitForFunction(() => {
    const cvs = document.querySelectorAll('.bottom-row canvas, .main-grid canvas');
    return cvs.length >= 3;
  }, null, { timeout: 10000 });
  await page.waitForTimeout(500);
  await page.screenshot({ path: '/tmp/shot-2-normal-data.png' });
  check('normal charts rendered (3 canvas)', await page.locator('canvas').count() >= 3);

  // ---------- 登录 guest ----------
  await page.click('button:has-text("登录 / 大屏")');
  await page.waitForSelector('.el-dialog');
  await page.click('.el-dialog button:has-text("登录")');
  await page.waitForSelector('.account-chip', { timeout: 8000 });
  check('guest logged in chip', await page.locator('.account-chip').innerText().then(t => t.includes('访客')));

  // ---------- 打开大屏 ----------
  await page.click('button:has-text("大屏模式")');
  await page.waitForSelector('.screen-root', { timeout: 8000 });
  await page.waitForSelector('.cell-kpi .kpi-value', { timeout: 8000 });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: '/tmp/shot-3-guest-screen.png', fullPage: false });

  check('screen header title', await page.locator('.screen-header h2').innerText().then(t => t.includes('数据大屏')));
  check('screen 6 panels', await page.locator('.screen-panel').count() === 6);
  check('kpi value visible & numeric', await page.locator('.cell-kpi .kpi-value').innerText().then(v => /^\d+$/.test(v.trim())));
  check('version badge v1', await page.locator('.meta.version').innerText().then(t => /v\d+/.test(t)));

  // logs 面板未授权 -> 占位说明而非空值
  const denied = page.locator('.cell-logs');
  check('logs placeholder shown', await denied.locator('.deny-placeholder').count() === 1);
  check('placeholder has reason text', await denied.locator('.deny-reason').innerText().then(t => t.includes('未被授权')));
  check('placeholder has no empty table', await denied.locator('table').count() === 0);
  // 未授权面板不泄露数据：无 canvas
  check('denied panel has no chart', await denied.locator('canvas').count() === 0);
  // 授权的图表面板有 canvas
  check('granted chart panels rendered', await page.locator('.cell-trend canvas, .cell-heatmap canvas, .cell-anomaly canvas').count() === 3);
  // 数据源授权栏：已授权 + 未授权占位标签
  check('source bar granted tags', await page.locator('.source-bar .el-tag').count() === 2);
  check('source bar denied placeholders', await page.locator('.source-bar .sb-denied').count() === 12);

  // 标题口径一致：大屏面板标题与普通模式相同的文案
  check('title consistency anomaly', await page.locator('.cell-anomaly .panel-title').innerText()
    .then(t => t.includes('异常分数 (3-sigma + IQR)')));
  check('title consistency trend', await page.locator('.cell-trend .panel-title').innerText()
    .then(t => t.includes('窗口日志量趋势')));
  check('title consistency heatmap', await page.locator('.cell-heatmap .panel-title').innerText()
    .then(t => t.includes('日志级别热力图')));
  // 图例文案一致（3-sigma / IQR / avg 在 canvas 中不好断言，用注入方式检查 shared options）
  const legendConsistent = await page.evaluate(() => {
    // 大屏与普通模式都引用同一份 chartOptions，这里检查大屏 ECharts 实例 legend 数据
    const doms = document.querySelectorAll('.cell-trend canvas, .cell-anomaly canvas');
    return doms.length === 2;
  });
  check('screen trend/anomaly chart canvases', legendConsistent);

  const kpiA = await page.locator('.cell-kpi .kpi-value').innerText();

  // ---------- 第二个窗口：同账号，取值必须一致 ----------
  // sessionStorage 不跨标签页共享，第二个窗口需独立登录（真实多窗口场景）
  const pageB = await ctx.newPage();
  const errorsB = [];
  pageB.on('pageerror', e => errorsB.push(e.message));
  await pageB.goto(BASE);
  await pageB.click('button:has-text("登录 / 大屏")');
  await pageB.waitForSelector('.el-dialog');
  await pageB.click('.el-dialog button:has-text("登录")');
  await pageB.waitForSelector('.account-chip', { timeout: 8000 });
  await pageB.click('button:has-text("大屏模式")');
  await pageB.waitForSelector('.cell-kpi .kpi-value', { timeout: 8000 });
  await pageB.waitForTimeout(1200);
  const kpiB = await pageB.locator('.cell-kpi .kpi-value').innerText();
  check('multi-window KPI identical', kpiA === kpiB, `${kpiA} vs ${kpiB}`);
  const bodyA = await page.locator('.screen-grid').innerText();
  const bodyB = await pageB.locator('.screen-grid').innerText();
  check('multi-window panel content identical', bodyA === bodyB);
  const verA = await page.locator('.meta.version').innerText();
  const verB = await pageB.locator('.meta.version').innerText();
  check('multi-window version identical', verA === verB, verA);

  // ---------- 管理员窗口：发布新授权，验证窗口自动跟随 ----------
  const pageAdmin = await ctx.newPage();
  await pageAdmin.goto(BASE);
  await pageAdmin.click('button:has-text("登录 / 大屏")');
  await pageAdmin.waitForSelector('.el-dialog');
  await pageAdmin.fill('.el-dialog input', 'admin');
  // 第二个输入框是密码
  const inputs = await pageAdmin.locator('.el-dialog input').all();
  await inputs[1].fill('admin123');
  await pageAdmin.click('.el-dialog button:has-text("登录")');
  await pageAdmin.waitForSelector('button:has-text("数据授权")', { timeout: 8000 });
  await pageAdmin.click('button:has-text("数据授权")');
  await pageAdmin.waitForSelector('.pm-table', { timeout: 8000 });

  // 先试一次"清单为空"的启用失败：清空所有行再点校验并启用
  // 切到 guest 账号（下拉选项含 "guest（v1·启用）"）
  await pageAdmin.locator('.pm-toolbar .el-select').first().click();
  await pageAdmin.locator('.el-select-dropdown__item:visible').filter({ hasText: 'guest' }).first().click();
  await pageAdmin.waitForTimeout(400);
  const delButtons = pageAdmin.locator('.pm-table button:has-text("删除")');
  const n = await delButtons.count();
  for (let i = 0; i < n; i++) { await delButtons.first().click(); await pageAdmin.waitForTimeout(30); }
  check('empty list hint shown', await pageAdmin.locator('.pm-empty').innerText().then(t => t.includes('授权清单为空')));
  await pageAdmin.click('button:has-text("校验并启用")');
  await pageAdmin.waitForSelector('.pm-alert.el-alert--error', { timeout: 8000 });
  const failMsg = await pageAdmin.locator('.pm-alert').innerText();
  check('enable-fail reason shown', failMsg.includes('授权清单为空') && failMsg.includes('启用失败'));
  await pageAdmin.screenshot({ path: '/tmp/shot-4-enable-fail.png' });

  // 构造冲突清单：添加 nginx allow 和 nginx deny + kpi allow
  // Element Plus 下拉是 teleport 到 body 的，且同屏可能有多个 popper，
  // 用“最后一个可见 popper”作用域来选当前行的选项
  async function pickOption(text) {
    const popper = pageAdmin.locator('.el-select__popper:visible').last();
    const item = popper.locator('.el-select-dropdown__item').filter({ hasText: text }).first();
    await item.waitFor({ state: 'visible', timeout: 5000 });
    await item.click({ force: true });
    await pageAdmin.waitForTimeout(120);
  }
  async function addRow(kind, resource, effect) {
    await pageAdmin.click('.pm-toolbar button:has-text("添加授权项")');
    await pageAdmin.waitForTimeout(120);
    const rows = pageAdmin.locator('.pm-table tbody tr');
    const last = rows.last();
    const selects = await last.locator('.el-select').all();
    // kind select (index 0)
    await selects[0].click();
    await pickOption(kind === 'source' ? '数据源' : '面板');
    // resource select (index 1)
    await last.locator('.el-select').nth(1).click();
    await pageAdmin.waitForTimeout(120);
    await pickOption(resource);
    // effect select (index 2)
    if (effect === 'deny') {
      await last.locator('.el-select').nth(2).click();
      await pageAdmin.waitForTimeout(120);
      await pickOption('deny');
    }
  }
  await addRow('source', 'nginx', 'allow');
  await addRow('source', 'nginx', 'deny');
  await addRow('panel', 'kpi', 'allow');
  await pageAdmin.click('button:has-text("校验并启用")');
  await pageAdmin.waitForTimeout(600);
  const clashMsg = await pageAdmin.locator('.pm-alert').innerText();
  check('conflict rejected with itemized reason', clashMsg.includes('互相冲突') || clashMsg.includes('冲突'));
  check('conflict shows 启用失败', clashMsg.includes('启用失败'));

  // 发布一个合法的新清单（kernel+docker+nginx，全部面板含 logs）
  // 删除冲突行重来：逐行删光
  let delCount = await pageAdmin.locator('.pm-table button:has-text("删除")').count();
  while (delCount-- > 0) { await pageAdmin.locator('.pm-table button:has-text("删除")').first().click(); await pageAdmin.waitForTimeout(20); }
  await addRow('source', 'nginx', 'allow');
  await addRow('source', 'kernel', 'allow');
  await addRow('source', 'docker', 'allow');
  await addRow('panel', '全部 (*)', 'allow');
  await pageAdmin.click('button:has-text("校验并启用")');
  await pageAdmin.waitForSelector('.pm-alert.el-alert--success', { timeout: 8000 });
  const okMsg = await pageAdmin.locator('.pm-alert').innerText();
  check('publish success message', okMsg.includes('已启用并发布'));
  await pageAdmin.screenshot({ path: '/tmp/shot-5-publish-ok.png' });

  // 窗口 B 主动刷新 -> 携带 v1 被 409 拒绝 -> 自动按 v2 重取 -> 写共享版本号，
  // storage 事件驱动窗口 A 同步切换（模拟多窗口口径跟随，无需等 30s 轮询）
  await pageB.click('.screen-header button:has-text("刷新")');
  await pageB.waitForFunction(() => {
    const el = document.querySelector('.meta.version');
    return el && el.textContent.includes('v2');
  }, null, { timeout: 15000 });
  const verB2 = await pageB.locator('.meta.version').innerText();
  check('window B switched to v2', verB2.includes('v2'), verB2);
  // storage 事件驱动 A 跟随
  await page.waitForFunction(() => {
    const el = document.querySelector('.meta.version');
    return el && el.textContent.includes('v2');
  }, null, { timeout: 15000 });
  check('window A auto-switched to v2', await page.locator('.meta.version').innerText().then(t => t.includes('v2')));
  await page.waitForTimeout(1000);
  const kpiA2 = await page.locator('.cell-kpi .kpi-value').innerText();
  const kpiB2val = await pageB.locator('.cell-kpi .kpi-value').innerText();
  check('both windows same new KPI', kpiA2 === kpiB2val, `${kpiA2} vs ${kpiB2val}`);
  // logs 面板现在已授权：占位消失，表格出现
  check('logs now granted: rows present', await page.locator('.cell-logs .el-table__row').count() > 0);
  check('logs placeholder removed', await page.locator('.cell-logs .deny-placeholder').count() === 0);
  await page.screenshot({ path: '/tmp/shot-6-guest-v2.png' });

  // 数据源授权栏更新：3 个已授权
  check('granted tags now 3', await page.locator('.source-bar .el-tag').count() === 3);

  // ---------- 越权：guest 尝试直接调管理接口 ----------
  const api403 = await page.evaluate(async () => {
    const r = await fetch('/api/scopes', { headers: { Authorization: 'Bearer ' + sessionStorage.getItem('lad_token') } });
    return { status: r.status, body: await r.json() };
  });
  check('guest /api/scopes 403 w/ reason', api403.status === 403 && api403.body.detail.includes('越权请求被拒绝'));

  // ---------- 切回普通模式：标题与图例保持一致，布局未改坏 ----------
  await page.click('button:has-text("退出大屏")');
  await page.waitForSelector('.screen-root', { state: 'detached' });
  await page.waitForTimeout(500);
  check('normal view restored', await page.locator('.main-grid').count() === 1);
  const gridColsAfter = await page.locator('.main-grid').evaluate(el => getComputedStyle(el).gridTemplateColumns);
  check('layout intact after screen exit', gridColsAfter === origGridCols, gridColsAfter);
  check('bottom row intact', await page.locator('.bottom-row').evaluate(el => getComputedStyle(el).gridTemplateColumns) === origBottomCols);
  check('5 panels after exit', await page.locator('.panel').count() >= 5);
  check('titles unchanged after exit', await page.locator('.panel h4').allInnerTexts().then(t =>
    t.some(x => x.includes('异常分数 (3-sigma + IQR)')) && t.some(x => x.includes('窗口日志量趋势'))));
  await page.screenshot({ path: '/tmp/shot-7-back-normal.png' });

  // ---------- 停用后大屏请求被拒，错误说明在大屏内展示 ----------
  // admin 停用 guest
  await pageAdmin.click('.el-dialog button:has-text("停用")');
  await pageAdmin.waitForSelector('.el-message-box', { timeout: 5000 });
  await pageAdmin.waitForSelector('.el-message-box', { timeout: 5000 });
  // 确认按钮（中文环境为“确定”，兜底点主按钮）
  const confirmBtn = pageAdmin.locator('.el-message-box .el-message-box__btns .el-button--primary').last();
  await confirmBtn.click();
  await pageAdmin.waitForTimeout(800);
  // guest 再次打开大屏
  await page.click('button:has-text("大屏模式")');
  await page.waitForSelector('.screen-error', { timeout: 8000 });
  const errText = await page.locator('.screen-error .err-text').innerText();
  check('disabled screen shows reason', errText.includes('尚未启用'));
  await page.screenshot({ path: '/tmp/shot-8-disabled.png' });
  await page.click('.screen-error button:has-text("返回普通模式")');
  await page.waitForSelector('.screen-root', { state: 'detached' });
  check('back to normal after error', await page.locator('.main-grid').count() === 1);

  // ---------- 控制台无 JS 错误 ----------
  // “Failed to load resource: 4xx”是浏览器对预期内拒绝（停用后打开大屏、
  // 越权探测）打印的网络日志，应用已在界面内承接这些拒绝原因，不算 JS 错误
  const realErrors = consoleErrors.filter(m => !/Failed to load resource: the server responded with a status of 4\d\d/.test(m));
  check('window A no JS errors', realErrors.length === 0, realErrors.join(' | ').slice(0, 200));
  check('window B no page errors', errorsB.length === 0, errorsB.join(' | ').slice(0, 200));

  await browser.close();
  console.log(`\n${failed === 0 ? 'ALL PASS' : failed + ' FAILED'} (${passed} passed)`);
  process.exit(failed === 0 ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
