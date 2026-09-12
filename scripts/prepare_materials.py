#!/usr/bin/env python3
import json,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'doc'/'MarkdownFiles'
OUT=ROOT/'common'/'materials'
MAPPING={
 '产品设计程序与_复习资料.md': ('product-design','产品设计程序与复习资料','产品设计程序'),
 '工业设计史_复习资料.md': ('industrial-design-history','工业设计史复习资料','工业设计史'),
 '机械制图基础(本)_复习资料.md': ('mechanical-drawing','机械制图基础（本）复习资料','机械制图基础'),
 '计算机辅助产品设计_复习资料.md': ('caid','计算机辅助产品设计复习资料','计算机辅助产品设计'),
}

def clean_cell(s):
    s=s.strip()
    if s.startswith('`') and s.endswith('`') and len(s)>=2: s=s[1:-1]
    return s

def parse_table(lines,i):
    header=lines[i]
    if i+1>=len(lines): return None,i
    sep=lines[i+1].strip()
    if '|' not in header or not re.match(r'^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$',sep):
        return None,i
    def cells(x):
        x=x.strip().strip('|')
        return [clean_cell(c) for c in x.split('|')]
    h=cells(header); rows=[]; j=i+2
    while j<len(lines):
        s=lines[j].strip()
        if not s or '|' not in s: break
        rows.append(cells(s)); j+=1
    return (h,rows),j

def block(bid,typ,level=0,text='',label='',marker='',ordered=False,headers=None,rows=None,depth=0):
    if headers is None: headers=['']
    if rows is None: rows=[['']]
    return {'id':bid,'type':typ,'level':level,'text':text,'label':label,'marker':marker,'ordered':ordered,'headers':headers,'rows':rows,'depth':depth}

def parse_md(text):
    lines=text.replace('\r\n','\n').replace('\r','\n').lstrip('\ufeff').split('\n')
    blocks=[]; sections=[]; current=None; parent_stack=[]; n=1; i=0
    def add_block(typ,level=0,text='',label='',marker='',ordered=False,headers=None,rows=None,depth=0):
        nonlocal n,current
        bid=f'blk-{n:03d}'; n+=1
        b=block(bid,typ,level,text,label,marker,ordered,headers,rows,depth)
        blocks.append(b)
        if current is not None: current['blockIds'].append(bid)
    while i<len(lines):
        line=lines[i]
        if not line.strip(): i+=1; continue
        m=re.match(r'^\s*(#{1,6})\s+(.+?)\s*#*\s*$',line)
        if m:
            lev=len(m.group(1)); title=m.group(2).strip()
            add_block('heading',lev,title)
            if lev<=2:
                if lev==1: parent_stack=[None]
                parent_id=parent_stack[0] if lev==2 and parent_stack else None
                sid=f'sec-{len(sections)+1:03d}'
                sec={'id':sid,'title':title,'level':lev,'parentId':parent_id,'blockIds':[blocks[-1]['id']]}
                sections.append(sec)
                if lev==1: parent_stack=[sid]
                current=sec
            i+=1; continue
        table,j=parse_table(lines,i)
        if table:
            h,rows=table; add_block('table',0,'','', '',False,h,rows,0); i=j; continue
        lm=re.match(r'^\s*([-+*]|\d+[.)])\s+(.+)$',line)
        if lm:
            marker=lm.group(1); txt=lm.group(2).strip(); ordered=bool(re.match(r'^\d',marker))
            add_block('list_item',0,txt,'',marker,ordered); i+=1; continue
        if re.match(r'^\s*>',line):
            q=[]
            while i<len(lines) and re.match(r'^\s*>',lines[i]):
                q.append(re.sub(r'^\s*>\s?','',lines[i]).strip()); i+=1
            add_block('quote',0,'\n'.join(q)); continue
        if line.strip().startswith('```'):
            fence=line.strip()[:3]; i+=1; code=[]
            while i<len(lines) and not lines[i].strip().startswith(fence): code.append(lines[i]); i+=1
            if i<len(lines): i+=1
            add_block('paragraph',0,'\n'.join(code)); continue
        para=[line.strip()]; i+=1
        while i<len(lines) and lines[i].strip() and not re.match(r'^\s*(#{1,6})\s+',lines[i]) and not re.match(r'^\s*([-+*]|\d+[.)])\s+',lines[i]) and not re.match(r'^\s*>',lines[i]) and '|' not in lines[i]:
            para.append(lines[i].strip()); i+=1
        txt='\n'.join(para)
        km=re.match(r'^\s*\*\*(.+?)\*\*\s*[：:]\s*(.+)$',txt)
        if km: add_block('kv',0,km.group(2).strip(),km.group(1).strip())
        else: add_block('paragraph',0,txt)
    return sections,blocks

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    index=[]; missing=[]
    for fn,(mid,title,subject) in MAPPING.items():
        p=SRC/fn
        if not p.exists(): missing.append(fn); continue
        sections,blocks=parse_md(p.read_text(encoding='utf-8'))
        data={'schemaVersion':1,'id':mid,'title':title,'subject':subject,'sections':sections,'blocks':blocks}
        (OUT/f'{mid}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        index.append({'id':mid,'title':title,'subject':subject,'file':f'{mid}.json','sectionCount':len(sections),'blockCount':len(blocks),'updatedAt':'2026-09-12'})
        print(f'{mid}: sections={len(sections)} blocks={len(blocks)}')
    if missing: raise SystemExit('Missing Markdown: '+', '.join(missing))
    (OUT/'index.json').write_text(json.dumps({'schemaVersion':1,'materials':index},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__': main()
