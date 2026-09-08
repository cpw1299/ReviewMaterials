const PAGE_PATH = '/pages/template/interstitial-poster/interstitial-poster'
const WAIT_FOR_RENDER = 3000

describe('template-interstitial-poster', () => {
  let page

  async function isPosterRendered() {
    const cardEl = await page.$('.poster-card')
    return cardEl != null
  }

  async function waitForPosterRendered(rendered) {
    const start = Date.now()
    await page.waitFor(async () => {
      return await isPosterRendered() == rendered || Date.now() - start > WAIT_FOR_RENDER
    })
    expect(await isPosterRendered()).toBe(rendered)
  }

  async function waitForPosterLifecycleCount(dataKey, previousCount) {
    const start = Date.now()
    await page.waitFor(async () => {
      return await page.data(dataKey) > previousCount || Date.now() - start > WAIT_FOR_RENDER
    })
    expect(await page.data(dataKey)).toBeGreaterThan(previousCount)
  }

  async function openPoster() {
    const enterCount = await page.data('testData.testPosterEnterCount')
    const button = await page.$('.hero-button')
    expect(button).not.toBeNull()
    await button.tap()
    await waitForPosterLifecycleCount('testData.testPosterEnterCount', enterCount)
    await waitForPosterRendered(true)
  }

  async function tapAndWaitForPosterClosed(tapHandler) {
    const leaveCount = await page.data('testData.testPosterLeaveCount')
    await tapHandler()
    await waitForPosterLifecycleCount('testData.testPosterLeaveCount', leaveCount)
  }

  beforeAll(async () => {
    page = await program.reLaunch(PAGE_PATH)
    await page.waitFor('view')
    await waitForPosterRendered(false)
  })

  beforeEach(async () => {
    await waitForPosterRendered(false)
  })

  it('renders hero content', async () => {
    const title = await page.$('.hero-title')
    expect(await title.text()).toBe('插屏海报示例')
    const desc = await page.$('.hero-desc')
    expect(await desc.text()).toBe('使用 page-container 实现一个居中的插屏海报。')
    const button = await page.$('.hero-button')
    expect(await button.text()).toBe('打开插屏海报')
    await waitForPosterRendered(false)
  })

  it('opens poster by tapping the primary button', async () => {
    await openPoster()
    const posterTitle = await page.$('.poster-title')
    expect(await posterTitle.text()).toBe('插屏海报')
    const posterAction = await page.$('.poster-action')
    expect(await posterAction.text()).toBe('立即查看')
    const posterCard = await page.$('.poster-card')
    const { width, height } = await posterCard.size()
    expect(width).toBeGreaterThan(0)
    expect(height).toBeGreaterThan(0)
    expect(posterAction).not.toBeNull()
    await tapAndWaitForPosterClosed(async () => {
      await posterAction.tap()
    })
  })

  it('closes poster by tapping the action button', async () => {
    await openPoster()
    const posterAction = await page.$('.poster-action')
    expect(posterAction).not.toBeNull()
    await tapAndWaitForPosterClosed(async () => {
      await posterAction.tap()
    })
  })

  it('closes poster by tapping the close button', async () => {
    await openPoster()
    const closeWrap = await page.$('.poster-close-wrap')
    expect(closeWrap).not.toBeNull()
    await tapAndWaitForPosterClosed(async () => {
      await closeWrap.tap()
    })
  })
})
