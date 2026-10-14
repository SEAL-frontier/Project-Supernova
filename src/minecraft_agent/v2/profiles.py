"""Read Spark protobuf profiles using upstream spark_sampler.proto field numbers.
Schema: https://github.com/lucko/spark/tree/master/spark-common/src/main/proto/spark
No viewer HTTP download is required. Weight percentages are samples, not proof of causation.
"""
import gzip, struct, zlib

def varint(raw,i):
    value=0;shift=0
    while i<len(raw) and shift<70:
        byte=raw[i];i+=1;value|=(byte&127)<<shift
        if not byte&128:return value,i
        shift+=7
    raise ValueError('Invalid protobuf varint')

def fields(raw):
    out={};i=0
    while i<len(raw):
        tag,i=varint(raw,i);number=tag>>3;wire=tag&7
        if wire==0:value,i=varint(raw,i)
        elif wire==1:
            value=struct.unpack('<d',raw[i:i+8])[0];i+=8
        elif wire==2:
            n,i=varint(raw,i)
            if n>len(raw)-i:raise ValueError('Truncated protobuf')
            value=raw[i:i+n];i+=n
        elif wire==5:value=raw[i:i+4];i+=4
        else:raise ValueError('Unsupported protobuf wire type')
        out.setdefault(number,[]).append(value)
    return out

def string(row,n):return row.get(n,[b''])[0].decode('utf-8','replace')
def doubles(row,n):
    out=[]
    for value in row.get(n,[]):
        if isinstance(value,bytes):
            if len(value)%8:raise ValueError('Malformed packed double')
            out.extend(struct.unpack('<'+'d'*(len(value)//8),value))
        else:out.append(value)
    return out
def integers(row,n):
    out=[]
    for value in row.get(n,[]):
        if isinstance(value,bytes):
            i=0
            while i<len(value):v,i=varint(value,i);out.append(v)
        else:out.append(value)
    return out

def analyze(raw):
    if raw.startswith(b'\x1f\x8b'):
        # Bound decompression to avoid accidental unbounded profile expansion.
        import io
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as f:raw=f.read(128*1024*1024+1)
    if len(raw)>128*1024*1024:raise ValueError('Expanded profile too large')
    data=fields(raw);metadata=fields(data.get(1,[b''])[0]);threads=data.get(2,[])
    if not threads:raise ValueError('No sampler threads found; unsupported/empty profile')
    sources={}
    for b in data.get(3,[]):
        item=fields(b);sources[string(item,1)]=string(item,2)
    hot=[];thread_totals=[];total=0
    for raw_thread in threads:
        thread=fields(raw_thread);name=string(thread,1);weight=sum(doubles(thread,4));total+=weight
        nodes=[fields(b) for b in thread.get(3,[])];weights=[sum(doubles(n,8)) for n in nodes]
        thread_totals.append({'thread':name,'weight':weight})
        for idx,node in enumerate(nodes):
            child_weight=sum(weights[x] for x in integers(node,9) if 0<=x<len(nodes))
            cls=string(node,3)
            hot.append({'thread':name,'class':cls,'method':string(node,4),'source':sources.get(cls),'inclusive_weight':weights[idx],'self_weight':max(0,weights[idx]-child_weight)})
    for row in hot:
        row['self_percent']=round(100*row['self_weight']/total,3) if total else 0
    return {'verified':True,'duration_seconds':(metadata.get(11,[0])[0]-metadata.get(2,[0])[0])/1000,
            'sampler_mode':metadata.get(15,[0])[0],'threads':thread_totals,'top_self':sorted(hot,key=lambda x:x['self_weight'],reverse=True)[:30],
            'note':'Sample-weight evidence only. Correlate load, slow ticks, logs and GC before attributing lag.'}
