#!/usr/bin/env python3
"""一次性静态一致性校验（不依赖 HBuilderX 编译）。

覆盖：
  A. 数据完整性：JSON 可解析、schema 形状统一、block/section 引用闭合、index.json 计数正确
  B. pages.json ↔ 页面文件 ↔ tabBar ↔ theme.json 变量
  C. manifest.json 资源存在 + 无 DCloud demo 凭据残留
  D. 全仓源码无指向已删除路径的引用
  E. loader.uts 静态导入 ↔ 磁盘文件 ↔ index.json id
  F. 样式规范：单类选择器、颜色必须走 var(--x, 亮色fallback)

用法：python scripts/check.py
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ERRORS = []
CHECKS = [0]


def err(msg):
    ERRORS.append(msg)


def ok():
    CHECKS[0] += 1


def rel(path):
    return os.path.relpath(path, ROOT).replace('\\', '/')


def read(path):
    with io.open(path, 'r', encoding='utf-8') as f:
        return f.read()


# ---------------------------------------------------------------- A. 数据
BLOCK_FIELDS = {
    'id': str, 'type': str, 'level': int, 'text': str, 'label': str,
    'marker': str, 'ordered': bool, 'headers': list, 'rows': list, 'depth': int,
}
KNOWN_TYPES = {'heading', 'paragraph', 'kv', 'list_item', 'table', 'quote'}


def check_data():
    index_path = os.path.join(ROOT, 'common/materials/index.json')
    try:
        index = json.loads(read(index_path))
        ok()
    except Exception as e:
        err('index.json 解析失败: %s' % e)
        return

    if index.get('schemaVersion') != 1:
        err('index.json schemaVersion != 1')
    materials = index.get('materials') or []
    if not materials:
        err('index.json materials 为空')

    ids = set()
    for m in materials:
        mid = m.get('id', '')
        if mid in ids:
            err('index.json 重复 id: %s' % mid)
        ids.add(mid)
        for field in ('id', 'title', 'subject', 'file', 'updatedAt'):
            if not isinstance(m.get(field), str) or not m[field]:
                err('index.json %s 缺字段 %s' % (mid, field))
        if not os.path.isfile(os.path.join(ROOT, 'common/materials', m.get('file', ''))):
            err('index.json 引用的文件不存在: %s' % m.get('file'))

    for m in materials:
        check_material(m, ids)


def check_material(m, ids):
    mid = m['id']
    path = os.path.join(ROOT, 'common/materials', m['file'])
    try:
        data = json.loads(read(path))
        ok()
    except Exception as e:
        err('%s 解析失败: %s' % (m['file'], e))
        return

    for field in ('schemaVersion', 'id', 'title', 'subject', 'sections', 'blocks'):
        if field not in data:
            err('%s 缺顶层字段 %s' % (mid, field))
    if data.get('id') != mid:
        err('%s 内部 id=%s 与索引不一致' % (m['file'], data.get('id')))

    blocks = data.get('blocks') or []
    block_ids = set()
    for b in blocks:
        bid = b.get('id', '')
        if bid in block_ids:
            err('%s 重复 block id: %s' % (mid, bid))
        block_ids.add(bid)
        if b.get('type') not in KNOWN_TYPES:
            err('%s %s 非法 type: %s' % (mid, bid, b.get('type')))
        for field, t in BLOCK_FIELDS.items():
            if field not in b:
                err('%s %s 缺字段 %s（统一形状被破坏，UTS 整体 as 会失败）' % (mid, bid, field))
            elif t is list:
                if not isinstance(b[field], list):
                    err('%s %s 字段 %s 应为 list' % (mid, bid, field))
            elif not isinstance(b[field], t):
                err('%s %s 字段 %s 应为 %s' % (mid, bid, field, t.__name__))
        if b.get('type') == 'table':
            if b.get('headers') and b.get('rows'):
                width = len(b['headers'])
                for r in b['rows']:
                    if len(r) != width:
                        err('%s %s 表格行宽不齐 %d != %d' % (mid, bid, len(r), width))
        if b.get('type') == 'kv' and not b.get('label'):
            err('%s %s kv 缺 label' % (mid, bid))

    sections = data.get('sections') or []
    sec_ids = set()
    for s in sections:
        sid = s.get('id', '')
        if sid in sec_ids:
            err('%s 重复 section id: %s' % (mid, sid))
        sec_ids.add(sid)
    for s in sections:
        sid = s.get('id', '')
        if s.get('level') not in (1, 2):
            err('%s %s level 应为 1/2，实际 %s' % (mid, sid, s.get('level')))
        if s.get('level') == 1 and s.get('parentId') is not None:
            err('%s %s level=1 但有 parentId' % (mid, sid))
        if s.get('level') == 2:
            pid = s.get('parentId')
            if pid not in sec_ids:
                err('%s %s parentId 悬空: %s' % (mid, sid, pid))
        for bid in s.get('blockIds') or []:
            if bid not in block_ids:
                err('%s %s blockIds 悬空: %s' % (mid, sid, bid))

    # 每 block 恰好归属一个 section
    owner = {}
    for s in sections:
        for bid in s.get('blockIds') or []:
            if bid in owner:
                err('%s block %s 同时挂在 %s 和 %s' % (mid, bid, owner[bid], s['id']))
            owner[bid] = s['id']
    for bid in block_ids:
        if bid not in owner:
            err('%s block %s 未被任何 section 引用' % (mid, bid))

    # index.json 计数 = 阅读单元数（拥有非 heading 内容的 section）
    btype = {b.get('id'): b.get('type') for b in blocks}
    units = [s for s in sections if any(btype.get(x) != 'heading' for x in s.get('blockIds') or [])]
    if m.get('sectionCount') != len(units):
        err('%s index.sectionCount=%s 但实际阅读单元 %d' % (mid, m.get('sectionCount'), len(units)))
    if m.get('blockCount') != len(blocks):
        err('%s index.blockCount=%s 但实际 %d' % (mid, m.get('blockCount'), len(blocks)))


# ---------------------------------------------------------------- B. pages.json
def check_pages():
    try:
        pages = json.loads(re.sub(r'^\s*//.*$', '', read(os.path.join(ROOT, 'pages.json')), flags=re.M))
        ok()
    except Exception as e:
        err('pages.json 解析失败: %s' % e)
        return

    paths = []
    for p in pages.get('pages') or []:
        path = p.get('path', '')
        paths.append(path)
        if not os.path.isfile(os.path.join(ROOT, path + '.uvue')):
            err('pages.json 指向不存在的页面: %s' % path)

    tab = pages.get('tabBar') or {}
    tab_list = tab.get('list') or []
    if len(tab_list) < 2:
        err('tabBar list 少于 2 项')
    for item in tab_list:
        page_path = item.get('pagePath', '')
        if page_path not in paths:
            err('tabBar pagePath 不在 pages 里: %s' % page_path)
        if not os.path.isfile(os.path.join(ROOT, page_path + '.uvue')):
            err('tabBar 指向不存在的页面: %s' % page_path)

    try:
        theme = json.loads(read(os.path.join(ROOT, 'theme.json')))
        ok()
    except Exception as e:
        err('theme.json 解析失败: %s' % e)
        return
    for mode in ('light', 'dark'):
        if mode not in theme:
            err('theme.json 缺 %s' % mode)
            continue
        keys = set(theme[mode].keys())
        gs = pages.get('globalStyle') or {}
        for key, v in gs.items():
            if isinstance(v, str) and v.startswith('@') and v[1:] not in keys:
                err('globalStyle @%s 在 theme.json %s 中不存在' % (v[1:], mode))
        for key, v in tab.items():
            if isinstance(v, str) and v.startswith('@') and v[1:] not in keys:
                err('tabBar @%s 在 theme.json %s 中不存在' % (v[1:], mode))


# ---------------------------------------------------------------- C. manifest.json
DEMO_CREDENTIALS = [
    'wxd1b990d3136e369c', '6917567445824957002', 'io.dcloud.uniappx',
    'io.dcloud.hellouniappx', 'hellouniappx', 'uniappxhello', '__UNI__48F9BA0',
]


def check_manifest():
    text = read(os.path.join(ROOT, 'manifest.json'))
    for token in DEMO_CREDENTIALS:
        if token in text:
            err('manifest.json 残留 demo 凭据: %s' % token)
    try:
        manifest = json.loads(text)
        ok()
    except Exception as e:
        err('manifest.json 解析失败: %s' % e)
        return
    for platform in ('app-android', 'app-ios'):
        icons = (manifest.get(platform) or {}).get('distribute', {}).get('icons', {})
        for key, v in icons.items():
            if not os.path.isfile(os.path.join(ROOT, v)):
                err('%s icons.%s 文件不存在: %s' % (platform, key, v))
    harmony = (manifest.get('app-harmony') or {}).get('distribute', {})
    for key in ('foreground', 'background'):
        v = (harmony.get('icons') or {}).get(key)
        if v and not os.path.isfile(os.path.join(ROOT, v)):
            err('app-harmony icons.%s 文件不存在: %s' % (key, v))
    v = (harmony.get('splashScreens') or {}).get('startWindowIcon')
    if v and not os.path.isfile(os.path.join(ROOT, v)):
        err('app-harmony splashScreens.startWindowIcon 不存在: %s' % v)


# ---------------------------------------------------------------- D. 死引用
DEAD_TOKENS = [
    'pages/component/', 'pages/template/', 'pages/tabBar/', 'uni_modules/',
    'wxcomponents/', 'uniCloud-aliyun/', 'hybrid/', '/workers/', 'static/',
    'store/index.uts', 'test-main-console', 'left-window', 'top-window',
]
SRC_EXTS = ('.uvue', '.uts', '.json', '.html', '.scss')


def check_dead_refs():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in ('.git', 'doc', 'package', 'harmony-configs', 'scripts', 'unpackage')]
        for name in filenames:
            if not name.endswith(SRC_EXTS):
                continue
            path = os.path.join(dirpath, name)
            text = read(path)
            for token in DEAD_TOKENS:
                if token in text:
                    err('%s 引用已删除路径: %s' % (rel(path), token))


# ---------------------------------------------------------------- E. loader
def check_loader():
    text = read(os.path.join(ROOT, 'common/materials/loader.uts'))
    imports = re.findall(r"import\s+\w+\s+from\s+'(\./[^']+\.json)'", text)
    if len(imports) < 5:
        err('loader.uts 静态导入 JSON 少于 5 个（index + 4 资料）: %s' % imports)
    for imp in imports:
        if not os.path.isfile(os.path.join(ROOT, 'common/materials', imp[2:])):
            err('loader.uts 导入的文件不存在: %s' % imp)

    index = json.loads(read(os.path.join(ROOT, 'common/materials/index.json')))
    for m in index['materials']:
        if ("id == '%s'" % m['id']) not in text:
            err('loader.uts loadMaterial 缺少分支: %s' % m['id'])

    store = read(os.path.join(ROOT, 'store/study.uts'))
    for token in ('loadMaterialIndex', 'loadMaterial', 'sectionById', 'readableSections'):
        if token not in store:
            err('store/study.uts 未引用 loader 的 %s' % token)


# ---------------------------------------------------------------- F. 样式规范
TAG_SELECTORS = re.compile(r'^(view|text|scroll-view|image|input|button|page|list-view)\s*[,{]')
DESCENDANT = re.compile(r'^\s*\.[A-Za-z0-9_-]+\s+(?!\.)?\S*\s*[,{]')
FIXED_COLOR = re.compile(r'^\s*[a-z-]+\s*:\s*(#[0-9a-fA-F]{3,8}|rgba?\()')


def check_styles():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in ('.git', 'doc', 'package', 'harmony-configs', 'scripts', 'unpackage')]
        for name in filenames:
            if not name.endswith(('.uvue', '.css')):
                continue
            path = os.path.join(dirpath, name)
            text = read(path)
            if name.endswith('.css'):
                style = text
            else:
                m = re.search(r'<style>([\s\S]*?)</style>', text)
                if not m:
                    continue
                style = m.group(1)
            in_media = 0
            in_ifdef = 0
            for lineno, line in enumerate(style.splitlines(), 1):
                stripped = line.strip()
                if '/* #' in stripped and '#ifdef' in stripped:
                    in_ifdef += 1
                elif '/* #' in stripped and '#endif' in stripped:
                    in_ifdef = max(0, in_ifdef - 1)
                if stripped.startswith('@media'):
                    in_media += 1
                elif stripped.startswith('}') and in_media:
                    in_media -= 1
                if '/*' in stripped:
                    continue
                if '!important' in stripped and in_ifdef == 0:
                    err('%s:%d 使用 !important' % (rel(path), lineno))
                if in_ifdef:
                    continue
                if re.match(r'^#[a-zA-Z]', stripped):
                    err('%s:%d 使用 ID 选择器' % (rel(path), lineno))
                if TAG_SELECTORS.match(stripped):
                    err('%s:%d 使用标签选择器: %s' % (rel(path), lineno, stripped))
                if re.match(r'^\.[A-Za-z0-9_-]+\s+[A-Za-z.][\w.-]*\s*[,{]\s*$', stripped):
                    err('%s:%d 疑似后代选择器: %s' % (rel(path), lineno, stripped))
                m2 = FIXED_COLOR.match(stripped)
                if m2 and 'var(' not in stripped and not stripped.startswith('--'):
                    err('%s:%d 固定色值未走 var()（暗黑模式不可用）: %s' % (rel(path), lineno, stripped))


BUILTIN_TAGS = {
    'view', 'text', 'image', 'scroll-view', 'list-view', 'swiper', 'swiper-item',
    'input', 'textarea', 'button', 'checkbox', 'checkbox-group', 'radio', 'radio-group',
    'switch', 'slider', 'picker', 'picker-view', 'picker-view-column', 'progress',
    'rich-text', 'video', 'canvas', 'map', 'web-view', 'navigator', 'form', 'label',
    'ad', 'cover-view', 'cover-image', 'template', 'block', 'slot', 'page-meta',
    'match-media', 'nested-scroll-header', 'nested-scroll-body', 'sticky-header',
    'uni-element', 'style', 'script',
}


def check_easycom():
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, 'pages')):
        for name in filenames:
            if not name.endswith('.uvue'):
                continue
            path = os.path.join(dirpath, name)
            text = read(path)
            m = re.search(r'<template>([\s\S]*?)</template>', text)
            if not m:
                continue
            for tag in set(re.findall(r'<([a-z][a-z0-9-]+)[\s>/]', m.group(1))):
                if tag in BUILTIN_TAGS or '-' not in tag:
                    continue
                comp = os.path.join(ROOT, 'components', tag, tag + '.uvue')
                if not os.path.isfile(comp):
                    err('%s 使用了不存在的组件 <%s>（easycom 需要 components/%s/%s.uvue）'
                        % (rel(path), tag, tag, tag))


def main():
    check_data()
    check_pages()
    check_manifest()
    check_dead_refs()
    check_loader()
    check_easycom()
    check_styles()
    print('检查项通过: %d' % CHECKS[0])
    if ERRORS:
        print('失败 %d 项:' % len(ERRORS))
        for e in ERRORS:
            print('  FAIL %s' % e)
        sys.exit(1)
    print('全部通过')


if __name__ == '__main__':
    main()
