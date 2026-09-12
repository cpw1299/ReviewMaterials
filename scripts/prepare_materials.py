#!/usr/bin/env python3
import json,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'doc'/'MarkdownFiles'
OUT=ROOT/'common'/'materials'
PARTS=OUT/'parts'
MAPPING={
 '产品设计程序与_复习资料.md': ('product-design','产品设计程序与复习资料','产品设计程序'),
 '工业设计史_复习资料.md': ('industrial-design-history','工业设计史复习资料','工业设计史'),
 '机械制图基础(本)_复习资料.md': ('mechanical-drawing','机械制图基础（本）复习资料','机械制图基础'),
 '计算机辅助产品设计_复习资料.md': ('caid','计算机辅助产品设计复习资料','计算机辅助产品设计'),
}

def clean_inline(s):
    s=s.strip()
    s=re.sub(r'!\[([^]]*)\]\([^)]*\)',r'\1',s)
    s=re.sub(r'\[([^]]+)\]\([^)]*\)',r'\1',s)
    s=re.sub(r'`([^`]+)`',r'\1',s)
    s=re.sub(r'\*\*([^*]+)\*\*',r'\1',s)
    s=re.sub(r'__([^_]+)__',r'\1',s)
    s=re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)',r'\1',s)
    s=re.sub(r'(?<!_)_([^_]+)_(?!_)',r'\1',s)
    s=re.sub(r'<br\s*/?>','\n',s,flags=re.I)
    s=s.replace('\u00a0',' ').replace('\u3000',' ')
    return s.strip()

def clean_cell(s):
    return clean_inline(s)

def parse_table(lines,i):
    header=lines[i]
    if i+1>=len(lines): return None,i
    sep=lines[i+1].strip()
    if '|' not in header or not re.match(r'^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$',sep):
        return None,i
    def cells(x):
        return [clean_cell(c) for c in x.strip().strip('|').split('|')]
    h=cells(header); rows=[]; j=i+2
    while j<len(lines):
        s=lines[j].strip()
        if not s or '|' not in s: break
        rows.append(cells(s)); j+=1
    return (h,rows),j

def block(bid,typ,level=0,text='',label='',marker='',ordered=False,headers=None,rows=None,depth=0):
    return {'id':bid,'type':typ,'level':level,'text':clean_inline(text),'label':clean_inline(label),'marker':marker,'ordered':ordered,'headers':headers or [''],'rows':rows or [['']],'depth':depth}

def parse_md(text):
    lines=text.replace('\r\n','\n').replace('\r','\n').lstrip('\ufeff').split('\n')
    heading_levels=[]
    for line in lines:
        m=re.match(r'^\s*(#{1,6})\s+(.+?)\s*#*\s*$',line)
        if m: heading_levels.append(len(m.group(1)))
    chapter_level=min(heading_levels) if heading_levels else 1
    section_level=chapter_level+1
    blocks=[]; sections=[]; current=None; parent_stack=[]; n=1; i=0
    def add_block(typ,level=0,text='',label='',marker='',ordered=False,headers=None,rows=None,depth=0):
        nonlocal n
        bid=f'blk-{n:04d}'; n+=1
        b=block(bid,typ,level,text,label,marker,ordered,headers,rows,depth)
        blocks.append(b)
        if current is not None: current['blockIds'].append(bid)
    while i<len(lines):
        line=lines[i]
        if not line.strip(): i+=1; continue
        m=re.match(r'^\s*(#{1,6})\s+(.+?)\s*#*\s*$',line)
        if m:
            lev=len(m.group(1)); title=clean_inline(m.group(2))
            add_block('heading',lev,title)
            if lev==chapter_level:
                sid=f'sec-{len(sections)+1:03d}'
                sec={'id':sid,'title':title,'level':1,'parentId':None,'blockIds':[blocks[-1]['id']]}
                sections.append(sec); parent_stack=[sid]; current=sec
            elif lev==section_level and parent_stack:
                sid=f'sec-{len(sections)+1:03d}'
                sec={'id':sid,'title':title,'level':2,'parentId':parent_stack[0],'blockIds':[blocks[-1]['id']]}
                sections.append(sec); current=sec
            i+=1; continue
        table,j=parse_table(lines,i)
        if table:
            h,rows=table; add_block('table',headers=h,rows=rows); i=j; continue
        lm=re.match(r'^\s*([-+*]|\d+[.)])\s+(.+)$',line)
        if lm:
            marker=lm.group(1); add_block('list_item',text=lm.group(2).strip(),marker=marker,ordered=bool(re.match(r'^\d',marker))); i+=1; continue
        if re.match(r'^\s*>',line):
            q=[]
            while i<len(lines) and re.match(r'^\s*>',lines[i]):
                q.append(re.sub(r'^\s*>\s?','',lines[i]).strip()); i+=1
            add_block('quote',text='\n'.join(q)); continue
        if line.strip().startswith('```'):
            fence=line.strip()[:3]; i+=1; code=[]
            while i<len(lines) and not lines[i].strip().startswith(fence): code.append(lines[i]); i+=1
            if i<len(lines): i+=1
            add_block('paragraph',text='\n'.join(code)); continue
        para=[line.strip()]; i+=1
        while i<len(lines) and lines[i].strip() and not re.match(r'^\s*(#{1,6})\s+',lines[i]) and not re.match(r'^\s*([-+*]|\d+[.)])\s+',lines[i]) and not re.match(r'^\s*>',lines[i]) and '|' not in lines[i]:
            para.append(lines[i].strip()); i+=1
        txt='\n'.join(para)
        km=re.match(r'^\s*\*\*(.+?)\*\*\s*[：:]\s*(.+)$',txt)
        if km: add_block('kv',text=km.group(2),label=km.group(1))
        else: add_block('paragraph',text=txt)
    return sections,blocks

def chapter_data(material_id,title,subject,chapter_index,section,blocks):
    ids=set(section['blockIds'])
    selected=[b for b in blocks if b['id'] in ids]
    return {'schemaVersion':1,'id':f'{material_id}-chapter-{chapter_index:02d}','title':section['title'],'subject':subject,'sections':[section],'blocks':selected}

def main():
    OUT.mkdir(parents=True,exist_ok=True); PARTS.mkdir(parents=True,exist_ok=True)
    index=[]; missing=[]
    for fn,(mid,title,subject) in MAPPING.items():
        p=SRC/fn
        if not p.exists(): missing.append(fn); continue
        sections,blocks=parse_md(p.read_text(encoding='utf-8'))
        data={'schemaVersion':1,'id':mid,'title':title,'subject':subject,'sections':sections,'blocks':blocks}
        (OUT/f'{mid}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        part_dir=PARTS/mid; part_dir.mkdir(parents=True,exist_ok=True)
        for old in part_dir.glob('chapter-*.json'): old.unlink()
        chapter_entries=[]
        chapters=[s for s in sections if s['level']==1]
        for ci,ch in enumerate(chapters,1):
            part=chapter_data(mid,title,subject,ci,ch,blocks)
            fn_part=f'chapter-{ci:02d}.json'
            (part_dir/fn_part).write_text(json.dumps(part,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            chapter_entries.append({'id':part['id'],'title':ch['title'],'file':fn_part,'sectionCount':1,'blockCount':len(part['blocks'])})
        (part_dir/'manifest.json').write_text(json.dumps({'schemaVersion':1,'id':mid,'title':title,'subject':subject,'chapters':chapter_entries},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        index.append({'id':mid,'title':title,'subject':subject,'file':f'{mid}.json','sectionCount':len(sections),'blockCount':len(blocks),'updatedAt':'2026-09-12'})
        print(f'{mid}: chapters={len(chapters)} sections={len(sections)} blocks={len(blocks)}')
    if missing: raise SystemExit('Missing Markdown: '+', '.join(missing))
    (OUT/'index.json').write_text(json.dumps({'schemaVersion':1,'materials':index},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__': main()
