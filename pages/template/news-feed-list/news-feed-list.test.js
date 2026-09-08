const platformInfo = process.env.uniTestPlatformInfo.toLocaleLowerCase()
const isWeb = platformInfo.startsWith('web')
const isMpAlipay = platformInfo === 'mp-alipay'
const isTablet =
  platformInfo.includes('平板') ||
  platformInfo.includes('matepad') ||
  platformInfo.includes('ipad')

const PAGE_PATH = '/pages/template/news-feed-list/news-feed-list'
const DETAIL_PAGE_PATH = 'pages/template/news-feed-list/detail/detail'

describe('template-news-feed-list', () => {
  if (isMpAlipay) {
    it('not support', () => {
      expect(1).toBe(1)
    })
    return
  }

  let page

  async function openListPage(useMockData = false) {
    page = await program.reLaunch(PAGE_PATH)
    await page.waitFor('view')
    await page.waitFor('text')
    if (useMockData) {
      await page.callMethod('jest_applyMockData')
      await waitForElements('.uni-list-cell')
    }
  }

  async function getState() {
    return await page.callMethod('jest_getState')
  }

  async function waitForListData(minCount = 1, attempts = 15) {
    for (let index = 0; index < attempts; index++) {
      const state = await getState()
      if (state.listCount >= minCount) {
        return state
      }
      await page.waitFor(200)
    }
    throw new Error(`list data did not reach count ${minCount}`)
  }

  async function waitForElements(selector, minCount = 1, attempts = 15) {
    for (let index = 0; index < attempts; index++) {
      const elements = await page.$$(selector)
      if (elements.length >= minCount) {
        return elements
      }
      await page.waitFor(200)
    }
    throw new Error(`elements for ${selector} did not reach count ${minCount}`)
  }

  async function waitForDetailState(expectedState, attempts = 15) {
    for (let index = 0; index < attempts; index++) {
      const state = await getState()
      const matched =
        state.isWideScreen === true &&
        state.currentIndex === expectedState.currentIndex &&
        state.title === expectedState.title &&
        state.postId === expectedState.postId &&
        state.cover === expectedState.cover
      if (matched) {
        return state
      }
      await page.waitFor(200)
    }
    throw new Error(`detail state did not reach title ${expectedState.title}`)
  }

  async function waitForElementText(selector, expectedText, attempts = 15) {
    for (let index = 0; index < attempts; index++) {
      const elements = await page.$$(selector)
      for (const element of elements) {
        if (await element.text() === expectedText) {
          return element
        }
      }
      await page.waitFor(200)
    }
    throw new Error(`element for ${selector} with text ${expectedText} did not appear`)
  }

  async function waitForCurrentPagePath(expectedPath, attempts = 10) {
    for (let index = 0; index < attempts; index++) {
      const currentPage = await program.currentPage()
      if (currentPage.path === expectedPath) {
        page = currentPage
        return currentPage
      }
      await page.waitFor(200)
    }
    throw new Error(`current page did not switch to ${expectedPath}`)
  }

  it('renders real list data in narrow layout', async () => {
    await openListPage()

    const state = await waitForListData()
    if (isTablet) {
      expect(true).toBe(true)
      return
    }
    expect(state.isWideScreen).toBe(false)
    expect(state.bannerTitle.length).toBeGreaterThan(0)
    expect(state.listCount).toBeGreaterThan(0)

    const bannerTitle = await page.$('.banner-title')
    expect((await bannerTitle.text()).length).toBeGreaterThan(0)
  })

  it('navigates to detail page and back in narrow layout', async () => {
    await openListPage()

    const listState = await waitForListData()
    if (isTablet) {
      expect(true).toBe(true)
      return
    }
    expect(listState.listCount).toBeGreaterThan(0)
    expect(listState.isWideScreen).toBe(false)

    const titles = await waitForElements('.uni-media-list-text-top')
    expect(titles.length).toBeGreaterThan(0)
    const firstTitleText = await titles[0].text()
    expect(firstTitleText.length).toBeGreaterThan(0)

    const items = await waitForElements('.uni-list-cell')
    expect(items.length).toBeGreaterThan(0)
    await items[0].tap()

    page = await waitForCurrentPagePath(DETAIL_PAGE_PATH)
    await page.waitFor('text')
    await page.waitFor(1000)
    const detailTitle = await page.$('.banner-title')
    expect(await detailTitle.text()).toBe(firstTitleText)

    await program.navigateBack()

    page = await waitForCurrentPagePath('pages/template/news-feed-list/news-feed-list')
    await page.waitFor('text')
    const backState = await waitForListData()
    expect(backState.isWideScreen).toBe(false)
    expect(backState.listCount).toBeGreaterThan(0)
  })

  it('shows detail in split view on tablet layout', async () => {
    if (!isTablet) {
      expect(true).toBe(true)
      return
    }

    await openListPage(true)

    const listState = await waitForListData()
    expect(listState.listCount).toBeGreaterThan(0)
    expect(listState.isWideScreen).toBe(true)

    const firstTitleText = '列表新闻一'
    const items = await waitForElements('.uni-list-cell')
    expect(items.length).toBeGreaterThan(0)
    await items[0].tap()

    await waitForElements('.detail-container')
    const wideState = await waitForDetailState({
      currentIndex: 0,
      postId: 'post-1',
      title: firstTitleText,
      cover: '/static/logo.png',
    })

    const currentPage = await program.currentPage()
    expect(currentPage.path).toBe('pages/template/news-feed-list/news-feed-list')
    expect(wideState.currentDetailContentLength).toBeGreaterThan(0)

    const detailTitle = await waitForElementText('.banner-title', firstTitleText)
    expect(await detailTitle.text()).toBe(firstTitleText)
  })

  it('shows the first detail in web split view', async () => {
    if (!isWeb) {
      expect(true).toBe(true)
      return
    }

    await openListPage(true)

    await page.callMethod('jest_setWideScreen', true)
    const opened = await page.callMethod('jest_openDetail', 0)
    expect(opened).toBe(true)
    await waitForElements('.detail-container')

    const state = await waitForDetailState({
      currentIndex: 0,
      postId: 'post-1',
      title: '列表新闻一',
      cover: '/static/logo.png',
    })
    expect(state.isWideScreen).toBe(true)
    expect(state.currentIndex).toBe(0)
    expect(state.postId).toBe('post-1')
    expect(state.title).toBe('列表新闻一')
    expect(state.cover).toBe('/static/logo.png')
    expect(state.currentDetailContentLength).toBeGreaterThan(0)

    const detailTitle = await waitForElementText('.banner-title', '列表新闻一')
    expect(await detailTitle.text()).toBe('列表新闻一')
  })

  it('switches to the second detail in web split view', async () => {
    if (!isWeb) {
      expect(true).toBe(true)
      return
    }

    await openListPage(true)

    await page.callMethod('jest_setWideScreen', true)
    await page.callMethod('jest_openDetail', 0)
    await waitForElements('.detail-container')

    const switched = await page.callMethod('jest_openDetail', 1)
    expect(switched).toBe(true)
    const nextState = await waitForDetailState({
      currentIndex: 1,
      postId: 'post-2',
      title: '列表新闻二',
      cover: '/static/shuijiao.jpg',
    })

    expect(nextState.isWideScreen).toBe(true)
    expect(nextState.currentIndex).toBe(1)
    expect(nextState.postId).toBe('post-2')
    expect(nextState.title).toBe('列表新闻二')
    expect(nextState.cover).toBe('/static/shuijiao.jpg')

    const detailTitle = await waitForElementText('.banner-title', '列表新闻二')
    expect(await detailTitle.text()).toBe('列表新闻二')
  })
})
