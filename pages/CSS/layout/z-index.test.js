const platformInfo = process.env.uniTestPlatformInfo.toLocaleLowerCase()
const isWeb = platformInfo.startsWith('web')
const isMpAlipay = platformInfo === 'mp-alipay'
const isAppWebView = process.env.UNI_AUTOMATOR_APP_WEBVIEW == 'true'

// 支付宝 Web 模拟器暂不支持 deviceShot，后续实现完整设备屏幕截图后恢复该用例。
const deviceShotIt = isMpAlipay ? it.skip : it

describe('css-z-index', () => {
  let page;
  beforeAll(async () => {
    page = await program.reLaunch('/pages/CSS/layout/z-index');
    await page.waitFor('view');
    await page.waitFor(isWeb ? 4000 : 2000);
  });

  // web 与 app 在某种情况下表现不同，不进行 app-webview 截图对比
  if (!isAppWebView) {
    deviceShotIt('screenshot', async () => {
      const windowInfo = await program.callUniMethod('getWindowInfo');
      const image = await program.screenshot({
        deviceShot: true,
        area: {
          x: 0,
          y: windowInfo.safeAreaInsets.top + 44
        }
      });
      expect(image).toSaveImageSnapshot();
    });
  }
});
