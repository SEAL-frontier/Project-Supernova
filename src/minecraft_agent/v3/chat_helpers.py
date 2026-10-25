"""Strict inexpensive chat helpers, independent of operational agents."""
import copy,logging,math,re
from pathlib import Path

_LOGGER=logging.getLogger(__name__)
_RENDER_ERROR_CODES=frozenset({
    "math_timeout", "unsupported_formula", "invalid_formula",
    "formula_too_complex", "formula_too_deep", "formula_too_large",
    "renderer_unavailable",
})
_FORMULA_COMMAND_NAMES=frozenset({
    "frac", "sqrt", "mathrm", "text", "pi", "sigma", "mu", "alpha", "beta",
    "gamma", "Delta", "theta", "omega", "sum", "int", "infty", "pm", "approx",
    "cdot", "times", "leq", "geq", "sin", "cos", "log", "exp", "quad", "left", "right",
})


def validate_calculations(value):
    if value is None:return []
    if not isinstance(value,list) or len(value)>4:raise ValueError('At most four calculations.')
    out=[];ids=set()
    for row in value:
        if not isinstance(row,dict) or set(row)!={'id','expression'}:raise ValueError('Invalid calculation fields.')
        ident,expr=row['id'],row['expression']
        if not isinstance(ident,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,24}',ident) or ident in ids:raise ValueError('Invalid calculation ID.')
        if not isinstance(expr,str) or not 1<=len(expr)<=256:raise ValueError('Invalid expression.')
        ids.add(ident);out.append({'id':ident,'expression':expr})
    return out


def validate_parts(value):
    if value is None:return []
    if not isinstance(value,list) or len(value)>8:raise ValueError('At most eight response parts.')
    out=[];images=0
    for row in value:
        if not isinstance(row,dict):raise ValueError('Invalid response part.')
        kind=row.get('type');field='text' if kind=='text' else 'formula' if kind=='formula' else None
        if not field or set(row)!={'type',field} or not isinstance(row[field],str):raise ValueError('Invalid response fields.')
        if not row[field].strip():continue
        if len(row[field])>(6000 if kind=='text' else 512):raise ValueError('Response part too long.')
        images+=kind=='formula'
        if images>2:raise ValueError('At most two formula images.')
        out.append(dict(row))
    return out


def _calculation_plan(value,seen):
    rows=validate_calculations(value)
    previous={r['id']:key for key,r in seen.items()}
    planned={}
    for row in rows:
        key=' '.join(re.findall(r'[A-Za-z_]\w*|\d+(?:\.\d*)?(?:[eE][+-]?\d+)?|\S',row['expression']))
        if row['id'] in previous and previous[row['id']]!=key:raise ValueError('Calculation ID reused.')
        if key not in seen:planned.setdefault(key,row)
    if len(seen)+len(planned)>4:raise ValueError('Calculation budget exhausted.')
    return list(planned.items())


def calculation_receipts(value,seen,math_module=None):
    if math_module is None:
        from . import chat_math as math_module
    out=[]
    for key,row in _calculation_plan(value,seen):
        try:
            result=math_module.calculate(row['expression'])
            if type(result) not in (int,float) or abs(result)>1e100 or not math.isfinite(result):
                raise ValueError('invalid_calculator_result')
            receipt={'id':row['id'],'expression':row['expression'],'verified':True,'result':result}
        except (ValueError,ArithmeticError) as exc:receipt={'id':row['id'],'expression':row['expression'],'verified':False,'error':str(exc)[:180]}
        seen[key]=receipt;out.append(receipt)
    return out


def render_parts(value, root, *, receipts=None):
    """Render off the gateway loop; optionally append formula-free preparation receipts.

    Receipts are not delivery claims. Existing part shapes and fallback voice stay intact.
    """
    from io import BytesIO
    from uuid import uuid4
    from PIL import Image
    from . import chat_math

    rows=validate_parts(value);out=[];failed=set()
    root=Path(root).resolve()
    for part_index,row in enumerate(rows):
        if row['type']=='text':
            text=discord_math_text(row['text']).strip()
            if text:out.append({'type':'text','text':text})
            continue
        if row['formula'] in failed:continue
        try:
            image=chat_math.render_formula(row['formula'])
            if (not isinstance(image,chat_math.FormulaImage) or not isinstance(image.png,bytes)
                or not 8<=len(image.png)<=chat_math.MAX_PNG_BYTES
                or not image.png.startswith(bytes.fromhex('89504e470d0a1a0a'))):
                raise ValueError('invalid_formula_image')
            with Image.open(BytesIO(image.png)) as decoded:
                width,height=decoded.size
                if (decoded.format!='PNG' or (width,height)!=(image.width,image.height)
                    or not 0<width<=chat_math.MAX_IMAGE_WIDTH
                    or not 0<height<=chat_math.MAX_IMAGE_HEIGHT
                    or width*height>chat_math.MAX_IMAGE_PIXELS or getattr(decoded,'n_frames',1)!=1):
                    raise ValueError('invalid_formula_image')
                decoded.load()
            root.mkdir(parents=True,exist_ok=True)
            path=root/(uuid4().hex+'.png')
            with path.open('xb') as stream:stream.write(image.png)
            out.append({'type':'image','path':str(path),'alt':'Công thức toán học'})
            if receipts is not None:
                receipts.append({'part_index':part_index,'prepared':True,'delivered':False})
        except (ValueError,ArithmeticError,OSError) as exc:
            formula=row['formula'];failed.add(formula)
            code=exc.code if isinstance(exc,chat_math.MathInputError) else None
            code=code if type(code) is str and code in _RENDER_ERROR_CODES else 'render_failed'
            commands={command if command in _FORMULA_COMMAND_NAMES else 'unsupported'
                      for command in re.findall(r'\\+([A-Za-z]+|[^A-Za-z])',formula)}
            _LOGGER.warning('formula_render_failed code=%s length=%d commands=%s',
                            code,len(formula),','.join(sorted(commands)) or 'none')
            if receipts is not None:
                receipts.append({'part_index':part_index,'prepared':False,'delivered':False,
                                 'error':code,'length':len(formula),'commands':sorted(commands)})
            text='Công thức '+str(len(failed))+': '+_formula_failure_text(formula)
            out.append({'type':'text','text':text})
    return out


def _formula_failure_text(formula):
    """Convert only the small bounded display subset, never execute TeX."""
    commands=re.findall(r'\\+([A-Za-z]+|[^A-Za-z])',formula)
    allowed=_FORMULA_COMMAND_NAMES | {',',';','!',' ','(',')','[',']'}
    depth=0;safe=True
    for char in formula:
        if char=='{':depth+=1
        elif char=='}':depth-=1
        if not 0<=depth<=12:safe=False
    safe=(safe and depth==0 and len(commands)<=64
          and all(command in allowed for command in commands)
          and re.fullmatch(r'[A-Za-z0-9+*/=^_{}()[\].,| :;<>!$\\-]+',formula))
    text=discord_math_text(formula) if safe else ''
    if safe:
        text=re.sub(r'([_^])\{([^{}]*)\}',r'\1(\2)',text)
        text=text.replace('{','(').replace('}',')')
    if (not text.strip() or any(c in text for c in '\\${}')
            or '[công thức chưa chuyển được]' in text):
        text='Không thể chuyển an toàn: cú pháp hoặc lệnh không hỗ trợ.'
    return 'Em chưa vẽ được công thức này; chưa có ảnh. Bản chữ: '+text


def discord_math_text(text):
    """Readable deterministic fallback; literal code/quotations are not math."""
    protected=r'(```[\s\S]*?```|`[^`\n]+`|^\s*>[^\n]*(?:\n|$)|"[^"\n]*"|“[^”\n]*”|‘[^’\n]*’|(?<!\w)\'[^\'\n]+\'(?!\w))'
    parts=re.split(protected,str(text),flags=re.M)
    symbols={'pi':'π','sigma':'σ','mu':'μ','alpha':'α','beta':'β','gamma':'γ',
             'Delta':'Δ','theta':'θ','omega':'ω','sum':'Σ','int':'∫','infty':'∞',
             'pm':'±','approx':'≈','cdot':'·','times':'×','leq':'≤','geq':'≥',
             'sin':'sin','cos':'cos','log':'log','exp':'exp','quad':' ',
             'left':'','right':''}
    for i in range(0,len(parts),2):
        value=parts[i]
        value=re.sub(r'\\+\((.*?)\\+\)',r'\1',value,flags=re.S)
        value=re.sub(r'\\+\[(.*?)\\+\]',r'\1',value,flags=re.S)
        value=re.sub(r'\$\$(.*?)\$\$',r'\1',value,flags=re.S)
        value=re.sub(r'\$([^$\n]*[A-Za-z\\^_{}=][^$\n]*)\$',r'\1',value)
        if re.search(r'\\+[A-Za-z]+',value):
            for _ in range(12):
                previous=value
                value=re.sub(r'\\+(?:mathrm|text)\{([A-Za-z0-9 +.,-]*)\}',r'\1',value)
                value=re.sub(r'\\+frac\{([^{}]*)\}\{([^{}]*)\}',r'(\1)/(\2)',value)
                value=re.sub(r'\\+sqrt\{([^{}]*)\}',r'√(\1)',value)
                if value==previous:break
            value=re.sub(r'\\+([A-Za-z]+)',lambda m:symbols.get(m[1],'[công thức chưa chuyển được]'),value)
            value=re.sub(r'\\+[,;! ]',' ',value)
            value=re.sub(r'([_^])\{([^{}]*)\}',r'\1(\2)',value)
            value=value.replace('{','(').replace('}',')')
        parts[i]=value
    return ''.join(parts)
