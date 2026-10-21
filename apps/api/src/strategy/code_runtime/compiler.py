"""검증된 닫힌 명세를 실제 Pine/Python/TypeScript 코드로 생성한다."""

from __future__ import annotations

import json
from typing import Any

from src.strategy.code_runtime.spec import (
    Condition,
    StrategySpec,
    UnsupportedStrategySpec,
    ValueRef,
)

# 복잡한 패턴을 비슷한 단순 전략으로 대체하지 않는다.
SUPPORTED_INDICATORS = frozenset(
    {
        "ema",
        "sma",
        "rsi",
        "atr",
        "highest",
        "lowest",
        "stdev",
        "obv",
        "donchian",
        "keltner",
        "atr_breakout",
        "macd",
        "bollinger",
        "roc",
        "stochastic",
        "cci",
        "williams_r",
        "vwap",
        "anchored_vwap",
        "cmf",
        "mfi",
        "aroon",
        "regression",
        "heikin_ashi",
        "chandelier",
    }
)


# 각 callback은 실제 런타임 안에서 한 봉만 추가한다. ctx.history는 현재 완료봉을 포함한다.
_PY_RUNTIME = r"""
def _qb_mean(values):
    base = values[0]
    return base + sum(value-base for value in values)/len(values)


def _qb_compare(a, b):
    if not (abs(a)<float("inf") and abs(b)<float("inf")): return None
    epsilon = 1e-12*max(1.0,abs(a),abs(b))
    return 0 if abs(a-b)<=epsilon else 1 if a>b else -1


def _qb_update(q, row):
    p = q["prices"]
    for key in ("open", "high", "low", "close", "volume"):
        p[key].append(float(row[key]))
    p["hlc3"].append(_qb_mean([p["high"][-1],p["low"][-1],p["close"][-1]]))
    o = q["outputs"]
    nan = float("nan")
    def avg(a, length):
        return _qb_mean(a[-length:]) if len(a)>=length else nan
    def ema(value, previous, length, key="value"):
        if not abs(value)<float("inf"): return previous if previous is not None else nan
        if previous is None or not abs(previous)<float("inf"):
            seed = mem.setdefault("ema_seed_"+key, [])
            seed.append(value)
            return _qb_mean(seed) if len(seed)>=length else nan
        alpha = 2.0/(length+1.0)
        return previous+alpha*(value-previous)
    for item in _QB_SPEC["indicators"]:
        ident, kind, length = item["id"], item["kind"], item["length"]
        s = p[item["source"]]
        mem = q["memory"].setdefault(ident, {})
        values = {}
        previous = mem.get("last")
        if kind == "ema":
            values["value"] = ema(s[-1], previous, length)
        elif kind in ("sma", "highest", "lowest", "stdev", "bollinger", "regression", "cci"):
            window = s[-length:]
            value = nan
            if len(window) == length:
                center = _qb_mean(window)
                sd = (sum((x-center)**2 for x in window)/length)**0.5
                if kind == "sma": value = center
                elif kind == "highest": value = max(window)
                elif kind == "lowest": value = min(window)
                elif kind == "stdev": value = sd
                elif kind == "bollinger":
                    values.update(upper=center+item["multiplier"]*sd, lower=center-item["multiplier"]*sd)
                    value = center
                elif kind == "cci":
                    mad = sum(abs(x-center) for x in window)/length
                    value = (s[-1]-center)/(0.015*mad) if mad else 0.0
                else:
                    mid = (length-1)/2
                    den = sum((i-mid)**2 for i in range(length))
                    slope = sum((i-mid)*(x-center) for i,x in enumerate(window))/den if den else 0.0
                    intercept = center-slope*mid
                    value = intercept+slope*(length-1)
                    residual = (sum((x-intercept-slope*i)**2 for i,x in enumerate(window))/length)**0.5
                    values.update(slope=slope, upper=value+item["multiplier"]*residual, lower=value-item["multiplier"]*residual)
            values["value"] = value
            if kind == "bollinger" and len(window)<length: values.update(upper=nan, lower=nan)
            if kind == "regression" and len(window)<length: values.update(slope=nan, upper=nan, lower=nan)
        elif kind == "donchian":
            hh,ll = (max(p["high"][-length:]),min(p["low"][-length:])) if len(s)>=length else (nan,nan)
            values.update(value=(hh+ll)/2,upper=hh,lower=ll)
        elif kind in ("rsi", "atr", "chandelier", "keltner", "atr_breakout"):
            if kind == "rsi":
                change = s[-1]-s[-2] if len(s)>1 else None
                if change is not None:
                    mem.setdefault("gains", []).append(max(change,0))
                    mem.setdefault("losses", []).append(max(-change,0))
                if len(mem.get("gains",[]))>=length:
                    gain = avg(mem["gains"],length) if "gain" not in mem else mem["gain"]+(mem["gains"][-1]-mem["gain"])/length
                    loss = avg(mem["losses"],length) if "loss" not in mem else mem["loss"]+(mem["losses"][-1]-mem["loss"])/length
                    mem.update(gain=gain,loss=loss)
                    values["value"] = 100-100/(1+gain/loss) if loss else 100.0
                else: values["value"] = nan
            else:
                high, low = p["high"][-1], p["low"][-1]
                prev = p["close"][-2] if len(s)>1 else p["close"][-1]
                tr = max(high-low, abs(high-prev), abs(low-prev))
                mem.setdefault("tr",[]).append(tr)
                atr = nan
                if len(s)>=length:
                    atr = avg(mem["tr"],length) if "atr" not in mem else mem["atr"]+(tr-mem["atr"])/length
                    mem["atr"] = atr
                if kind == "atr": values["value"] = atr
                elif kind == "keltner":
                    mid = ema(s[-1],previous,length)
                    values.update(value=mid,upper=mid+item["multiplier"]*atr,lower=mid-item["multiplier"]*atr)
                elif kind == "atr_breakout":
                    values.update(upper=p["close"][-1]+item["multiplier"]*atr,lower=p["close"][-1]-item["multiplier"]*atr)
                else: values.update(upper=min(p["low"][-length:])+item["multiplier"]*atr, lower=max(p["high"][-length:])-item["multiplier"]*atr)
        elif kind == "obv":
            change = p["close"][-1]-p["close"][-2] if len(s)>1 else 0
            values["value"] = (previous or 0)+p["volume"][-1]*(1 if change>0 else -1 if change<0 else 0)
            mem.setdefault("obv",[]).append(values["value"])
            values["signal"] = avg(mem["obv"],length)
        elif kind == "macd":
            mem["fast"] = ema(s[-1],mem.get("fast"),length,"fast")
            mem["slow"] = ema(s[-1],mem.get("slow"),item["slow"],"slow")
            value = mem["fast"]-mem["slow"]
            mem["signal"] = ema(value,mem.get("signal"),item["signal"],"signal")
            values.update(value=value,signal=mem["signal"])
        elif kind == "roc":
            values["value"] = 100*(s[-1]/s[-length-1]-1) if len(s)>length and s[-length-1] else nan
        elif kind in ("stochastic", "williams_r"):
            value = nan
            if len(s)>=length:
                hh, ll = max(p["high"][-length:]), min(p["low"][-length:])
                value = 100*(p["close"][-1]-ll)/(hh-ll) if hh!=ll else nan
            if kind == "williams_r": values["value"] = value-100
            else:
                mem.setdefault("raw",[]).append(value)
                k = avg(mem["raw"],item["slow"])
                mem.setdefault("k",[]).append(k)
                values.update(value=k,signal=avg(mem["k"],item["signal"]))
        elif kind in ("vwap", "anchored_vwap"):
            timestamp = row["timestamp"]
            # SDK가 UTC epoch milliseconds를 제공하면 날짜 문자열 형식에 의존하지 않는다.
            epoch = row.get("timestamp_ms")
            day = int(epoch)//86400000 if epoch is not None else str(timestamp)[:10]
            eligible = kind=="vwap" or epoch is not None and int(epoch)>=item["anchor_ms"]
            if kind=="anchored_vwap" and epoch is None:
                from datetime import datetime
                eligible = datetime.fromisoformat(str(timestamp).replace("Z","+00:00")).timestamp()*1000>=item["anchor_ms"]
            if kind=="vwap" and mem.get("day")!=day:
                mem.update(pv=0.0,volume=0.0,day=day)
            if eligible:
                mem["pv"] = mem.get("pv",0)+p["hlc3"][-1]*p["volume"][-1]
                mem["volume"] = mem.get("volume",0)+p["volume"][-1]
            values["value"] = mem.get("pv",0)/mem["volume"] if mem.get("volume",0)>0 else nan
        elif kind in ("cmf", "mfi"):
            volume = p["volume"][-1]
            if kind == "cmf":
                high,low,close = p["high"][-1],p["low"][-1],p["close"][-1]
                flow = ((2*close-high-low)/(high-low))*volume if high!=low else 0.0
                mem.setdefault("flow",[]).append(flow)
                den = sum(p["volume"][-length:])
                values["value"] = sum(mem["flow"][-length:])/den if len(s)>=length and den else nan
            else:
                change = p["hlc3"][-1]-p["hlc3"][-2] if len(s)>1 else 0
                flow = p["hlc3"][-1]*volume
                mem.setdefault("positive",[]).append(flow if change>0 else 0)
                mem.setdefault("negative",[]).append(flow if change<0 else 0)
                pos,neg = sum(mem["positive"][-length:]),sum(mem["negative"][-length:])
                values["value"] = (100-100/(1+pos/neg) if neg else 100.0 if pos else nan) if len(s)>length else nan
        elif kind == "aroon":
            if len(s)>length:
                highs,lows = p["high"][-length-1:],p["low"][-length-1:]
                hi = max(range(length+1),key=lambda i:(highs[i],i))
                lo = min(range(length+1),key=lambda i:(lows[i],-i))
                values.update(up=100*hi/length,down=100*lo/length)
            else: values.update(up=nan,down=nan)
        elif kind == "heikin_ashi":
            hc = (p["open"][-1]+p["high"][-1]+p["low"][-1]+p["close"][-1])/4
            ho = (mem["open"]+previous)/2 if previous is not None else (p["open"][-1]+p["close"][-1])/2
            mem["open"] = ho
            values.update(value=hc,open=ho)
        for output,value in values.items():
            o.setdefault(ident+"."+output,[]).append(value)
        mem["last"] = values.get("value")
    q["last"] = row["index"]


def _qb_ref(q, ref, extra=0):
    if ref["constant"] is not None: return ref["constant"]
    name = ref["series"]
    values = q["prices"].get(name) if name in q["prices"] else q["outputs"].get(name+"."+ref["output"],[])
    offset = ref["offset"]+extra
    return values[-1-offset] if len(values)>offset else float("nan")


def _qb_condition(q, node):
    op = node["op"]
    if op == "true": return True
    if op == "false": return False
    if op == "all": return all(_qb_condition(q,c) for c in node["children"])
    if op == "any": return any(_qb_condition(q,c) for c in node["children"])
    if op == "not": return not _qb_condition(q,node["children"][0])
    a,b = _qb_ref(q,node["left"]),_qb_ref(q,node["right"])
    comparison = _qb_compare(a,b)
    if comparison is None: return False
    if op == "gt": return comparison>0
    if op == "gte": return comparison>=0
    if op == "lt": return comparison<0
    if op == "lte": return comparison<=0
    pa,pb = _qb_ref(q,node["left"],1),_qb_ref(q,node["right"],1)
    previous = _qb_compare(pa,pb)
    if previous is None: return False
    return previous<=0 and comparison>0 if op=="cross_up" else previous>=0 and comparison<0


def on_bar(ctx, state):
    q = state.setdefault("_qb", {"prices":{k:[] for k in ("open","high","low","close","volume","hlc3")},"outputs":{},"memory":{},"last":-1})
    if q["last"] < 0:
        for row in ctx["history"]: _qb_update(q,row)
    elif ctx["bar"]["index"] > q["last"]:
        if ctx["bar"]["index"] != q["last"]+1: raise ValueError("봉 순서에 공백이 있습니다")
        _qb_update(q,ctx["bar"])
    if len(q["prices"]["close"])<_QB_SPEC["warmup_bars"]: return {"action":"hold"}
    long_signal,short_signal = _qb_condition(q,_QB_SPEC["long_entry"]),_qb_condition(q,_QB_SPEC["short_entry"])
    if long_signal and short_signal: return {"action":"hold"}
    direction = ctx["position"]["direction"]
    if long_signal and direction!="long": return {"action":"long"}
    if short_signal and direction!="short": return {"action":"short"}
    invalid = _QB_SPEC["long_invalidation"] if direction=="long" else _QB_SPEC["short_invalidation"]
    return {"action":"close" if direction!="flat" and _qb_condition(q,invalid) else "hold"}
"""

_TS_RUNTIME = r"""
function _qbMean(values:number[]):number{const base=values[0];return base+values.reduce((total,value)=>total+(value-base),0)/values.length;}
function _qbCompare(a:number,b:number):number{if(!Number.isFinite(a)||!Number.isFinite(b))return NaN;const epsilon=1e-12*Math.max(1,Math.abs(a),Math.abs(b));return Math.abs(a-b)<=epsilon?0:a>b?1:-1;}
function _qbUpdate(q:any,row:any):void {
 const p=q.prices,o=q.outputs, nan=NaN;
 for(const key of ["open","high","low","close","volume"]) p[key].push(Number(row[key]));
 p.hlc3.push(_qbMean([p.high.at(-1),p.low.at(-1),p.close.at(-1)]));
 const avg=(a:number[],n:number)=>a.length>=n?_qbMean(a.slice(-n)):nan;
 const ema=(x:number,prev:number|undefined,n:number,seed:number[])=>{if(!Number.isFinite(x))return prev??nan;if(prev===undefined||!Number.isFinite(prev)){seed.push(x);return seed.length>=n?_qbMean(seed):nan;}const alpha=2/(n+1);return prev+alpha*(x-prev);};
 for(const item of _QB_SPEC.indicators){
  const id=item.id,kind=item.kind,n=item.length,s=p[item.source],last=s.at(-1),m=q.memory[id]??(q.memory[id]={});
  const vals:any={},prev=m.last;
  if(kind==="ema") vals.value=ema(last,prev,n,(m.seedValue??=[]));
  else if(["sma","highest","lowest","stdev","bollinger","regression","cci"].includes(kind)){
   const w=s.slice(-n);let value=nan;
   if(w.length===n){
    const center=avg(w,n),sd=Math.sqrt(w.reduce((a:number,x:number)=>a+(x-center)**2,0)/n);
    if(kind==="sma")value=center;
    else if(kind==="highest")value=Math.max(...w);
    else if(kind==="lowest")value=Math.min(...w);
    else if(kind==="stdev")value=sd;
    else if(kind==="bollinger"){value=center;vals.upper=center+item.multiplier*sd;vals.lower=center-item.multiplier*sd;}
    else if(kind==="cci"){const mad=w.reduce((a:number,x:number)=>a+Math.abs(x-center),0)/n;value=mad?(last-center)/(.015*mad):0;}
    else{const mid=(n-1)/2,den=w.reduce((a:number,_:number,i:number)=>a+(i-mid)**2,0),slope=den?w.reduce((a:number,x:number,i:number)=>a+(i-mid)*(x-center),0)/den:0,intercept=center-slope*mid;
     value=intercept+slope*(n-1);const residual=Math.sqrt(w.reduce((a:number,x:number,i:number)=>a+(x-intercept-slope*i)**2,0)/n);Object.assign(vals,{slope,upper:value+item.multiplier*residual,lower:value-item.multiplier*residual});}
   }
   vals.value=value;if(w.length<n&&kind==="bollinger")Object.assign(vals,{upper:nan,lower:nan});if(w.length<n&&kind==="regression")Object.assign(vals,{slope:nan,upper:nan,lower:nan});
  }else if(kind==="donchian"){const hh=s.length>=n?Math.max(...p.high.slice(-n)):nan,ll=s.length>=n?Math.min(...p.low.slice(-n)):nan;Object.assign(vals,{value:(hh+ll)/2,upper:hh,lower:ll});}
  else if(["rsi","atr","chandelier","keltner","atr_breakout"].includes(kind)){
   if(kind==="rsi"){
    if(s.length>1){const d=last-s.at(-2);(m.gains??=[]).push(Math.max(d,0));(m.losses??=[]).push(Math.max(-d,0));}
    if((m.gains?.length??0)>=n){m.gain=m.gain===undefined?avg(m.gains,n):m.gain+(m.gains.at(-1)-m.gain)/n;m.loss=m.loss===undefined?avg(m.losses,n):m.loss+(m.losses.at(-1)-m.loss)/n;vals.value=m.loss?100-100/(1+m.gain/m.loss):100;}else vals.value=nan;
   }else{const h=p.high.at(-1),l=p.low.at(-1),pc=s.length>1?p.close.at(-2):p.close.at(-1),tr=Math.max(h-l,Math.abs(h-pc),Math.abs(l-pc));(m.tr??=[]).push(tr);let atr=nan;
    if(s.length>=n){atr=m.atr===undefined?avg(m.tr,n):m.atr+(tr-m.atr)/n;m.atr=atr;}
    if(kind==="atr")vals.value=atr;else if(kind==="keltner"){const mid=ema(last,prev,n,(m.seedValue??=[]));Object.assign(vals,{value:mid,upper:mid+item.multiplier*atr,lower:mid-item.multiplier*atr});}else if(kind==="atr_breakout")Object.assign(vals,{upper:p.close.at(-1)+item.multiplier*atr,lower:p.close.at(-1)-item.multiplier*atr});else Object.assign(vals,{upper:Math.min(...p.low.slice(-n))+item.multiplier*atr,lower:Math.max(...p.high.slice(-n))-item.multiplier*atr});}
  }else if(kind==="obv"){const d=s.length>1?p.close.at(-1)-p.close.at(-2):0;vals.value=(prev??0)+p.volume.at(-1)*(d>0?1:d<0?-1:0);(m.obv??=[]).push(vals.value);vals.signal=avg(m.obv,n);}
  else if(kind==="macd"){m.fast=ema(last,m.fast,n,(m.seedFast??=[]));m.slow=ema(last,m.slow,item.slow,(m.seedSlow??=[]));vals.value=m.fast-m.slow;m.signal=ema(vals.value,m.signal,item.signal,(m.seedSignal??=[]));vals.signal=m.signal;}
  else if(kind==="roc")vals.value=s.length>n&&s.at(-n-1)?100*(last/s.at(-n-1)-1):nan;
  else if(kind==="stochastic"||kind==="williams_r"){
   let value=nan;if(s.length>=n){const hh=Math.max(...p.high.slice(-n)),ll=Math.min(...p.low.slice(-n));value=hh!==ll?100*(p.close.at(-1)-ll)/(hh-ll):nan;}
   if(kind==="williams_r")vals.value=value-100;else{(m.raw??=[]).push(value);const k=avg(m.raw,item.slow);(m.k??=[]).push(k);Object.assign(vals,{value:k,signal:avg(m.k,item.signal)});}
  }else if(kind==="vwap"||kind==="anchored_vwap"){
   const epoch=row.timestamp_ms??Date.parse(row.timestamp),day=Math.floor(epoch/86400000),eligible=kind==="vwap"||epoch>=Number(item.anchor_ms);
   if(kind==="vwap"&&m.day!==day)Object.assign(m,{pv:0,volume:0,day});
   if(eligible){m.pv=(m.pv??0)+p.hlc3.at(-1)*p.volume.at(-1);m.volume=(m.volume??0)+p.volume.at(-1);}vals.value=m.volume>0?m.pv/m.volume:nan;
  }else if(kind==="cmf"||kind==="mfi"){
   const v=p.volume.at(-1);
   if(kind==="cmf"){const h=p.high.at(-1),l=p.low.at(-1),c=p.close.at(-1);(m.flow??=[]).push(h!==l?((2*c-h-l)/(h-l))*v:0);const den=p.volume.slice(-n).reduce((a:number,b:number)=>a+b,0);vals.value=s.length>=n&&den?m.flow.slice(-n).reduce((a:number,b:number)=>a+b,0)/den:nan;}
   else{const d=s.length>1?p.hlc3.at(-1)-p.hlc3.at(-2):0,f=p.hlc3.at(-1)*v;(m.positive??=[]).push(d>0?f:0);(m.negative??=[]).push(d<0?f:0);const pos=m.positive.slice(-n).reduce((a:number,b:number)=>a+b,0),neg=m.negative.slice(-n).reduce((a:number,b:number)=>a+b,0);vals.value=s.length>n?(neg?100-100/(1+pos/neg):pos?100:nan):nan;}
  }else if(kind==="aroon"){
   if(s.length>n){const hs=p.high.slice(-n-1),ls=p.low.slice(-n-1);let hi=0,lo=0;for(let i=1;i<=n;i++){if(hs[i]>=hs[hi])hi=i;if(ls[i]<=ls[lo])lo=i;}Object.assign(vals,{up:100*hi/n,down:100*lo/n});}else Object.assign(vals,{up:nan,down:nan});
  }else if(kind==="heikin_ashi"){const hc=(p.open.at(-1)+p.high.at(-1)+p.low.at(-1)+p.close.at(-1))/4,ho=prev!==undefined?(m.open+prev)/2:(p.open.at(-1)+p.close.at(-1))/2;m.open=ho;Object.assign(vals,{value:hc,open:ho});}
  for(const [key,value]of Object.entries(vals))(o[id+"."+key]??=[]).push(value);m.last=vals.value;
 }
 q.last=row.index;
}
function _qbRef(q:any,r:any,extra=0):number{if(r.constant!==null)return r.constant;const a=q.prices[r.series]??q.outputs[r.series+"."+r.output]??[],offset=r.offset+extra;return a.length>offset?a[a.length-1-offset]:NaN;}
function _qbCondition(q:any,c:any):boolean{
 const op=c.op;if(op==="true")return true;if(op==="false")return false;if(op==="all")return c.children.every((x:any)=>_qbCondition(q,x));if(op==="any")return c.children.some((x:any)=>_qbCondition(q,x));if(op==="not")return !_qbCondition(q,c.children[0]);
 const a=_qbRef(q,c.left),b=_qbRef(q,c.right),comparison=_qbCompare(a,b);if(!Number.isFinite(comparison))return false;
 if(op==="gt")return comparison>0;if(op==="gte")return comparison>=0;if(op==="lt")return comparison<0;if(op==="lte")return comparison<=0;const previous=_qbCompare(_qbRef(q,c.left,1),_qbRef(q,c.right,1));if(!Number.isFinite(previous))return false;return op==="cross_up"?previous<=0&&comparison>0:previous>=0&&comparison<0;
}
export function onBar(ctx:any,state:any):{action:string}{
 const q=state._qb??(state._qb={prices:{open:[],high:[],low:[],close:[],volume:[],hlc3:[]},outputs:{},memory:{},last:-1});
 if(q.last<0){for(const row of ctx.history)_qbUpdate(q,row);}else if(ctx.bar.index>q.last){if(ctx.bar.index!==q.last+1)throw new Error("noncontiguous bar sequence");_qbUpdate(q,ctx.bar);}
 if(q.prices.close.length<_QB_SPEC.warmup_bars)return{action:"hold"};const l=_qbCondition(q,_QB_SPEC.long_entry),s=_qbCondition(q,_QB_SPEC.short_entry),d=ctx.position.direction;
 if(l&&s)return{action:"hold"};if(l&&d!=="long")return{action:"long"};if(s&&d!=="short")return{action:"short"};return{action:d!=="flat"&&_qbCondition(q,d==="long"?_QB_SPEC.long_invalidation:_QB_SPEC.short_invalidation)?"close":"hold"};
}
"""


def _pine_at(name: str, offset: int | str) -> str:
    if name == "qb_hlc3":
        return f"(high[{offset}] + ((low[{offset}] - high[{offset}]) + (close[{offset}] - high[{offset}])) / 3.0)"
    return f"{name}[{offset}]"


def _pine_ref(ref: ValueRef, extra: int = 0) -> str:
    if ref.constant is not None:
        return repr(ref.constant)
    name = ref.series or ""
    if name == "hlc3":
        name = "qb_hlc3"
    elif name not in {"open", "high", "low", "close", "volume"}:
        name = f"qb_{name}_{ref.output}"
    offset = ref.offset + extra
    return _pine_at(name, offset) if offset else name


def _pine_condition(condition: Condition) -> str:
    op = condition.op
    if op in ("true", "false"):
        return op
    if op == "not":
        return f"not ({_pine_condition(condition.children[0])})"
    if op in ("all", "any"):
        joiner = " and " if op == "all" else " or "
        return "(" + joiner.join(_pine_condition(c) for c in condition.children) + ")"
    assert condition.left is not None and condition.right is not None
    a, b = _pine_ref(condition.left), _pine_ref(condition.right)

    def compare(left: str, right: str, operator: str) -> str:
        return f"(qb_finite({left}) and qb_finite({right}) and qb_compare({left}, {right}) {operator} 0)"

    if op in ("cross_up", "cross_down"):
        pa, pb = _pine_ref(condition.left, 1), _pine_ref(condition.right, 1)
        return (
            f"({compare(pa, pb, '<=')} and {compare(a, b, '>')})"
            if op == "cross_up"
            else f"({compare(pa, pb, '>=')} and {compare(a, b, '<')})"
        )
    operator = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<="}[op]
    return compare(a, b, operator)


def _pine_window(target: str, source: str, length: int, *, stdev: bool = False) -> list[str]:
    """NA를 무시한 극값만으로 상수 창을 주장하지 않는다. n개 유한 관측이 모두 필요하다."""
    calculation = "stdev" if stdev else "sma"
    constant = "0.0" if stdev else source
    return [
        f"{target}_raw = ta.{calculation}({source}, {length})",
        f"{target}_finite = ta.sma(qb_finite({source}) ? 1.0 : 0.0, {length})",
        f"{target}_hi = ta.highest({source}, {length})",
        f"{target}_lo = ta.lowest({source}, {length})",
        f"{target} = {target}_finite == 1.0 ? ({target}_hi == {target}_lo ? {constant} : {target}_raw) : na",
    ]


def _pine_smooth(target: str, source: str, length: int, *, rma: bool = False) -> list[str]:
    alpha = f"1.0 / {length}" if rma else f"2.0 / ({length} + 1.0)"
    return [
        *_pine_window(target + "_seed", source, length),
        f"var float {target} = na",
        f"{target} := not qb_finite({source}) ? {target}[1] : (not qb_finite({target}[1]) ? {target}_seed : {target}[1] + ({alpha}) * ({source} - {target}[1]))",
    ]


def _compile_pine(spec: StrategySpec) -> str:
    lines = [
        "//@version=5",
        "strategy("
        + json.dumps(spec.title, ensure_ascii=False)
        + ", process_orders_on_close=false)",
        "qb_finite(value) => not na(value) and math.abs(value) <= 1.7976931348623157e308",
        "qb_compare(a, b) =>",
        "    epsilon = 1e-12 * math.max(1.0, math.max(math.abs(a), math.abs(b)))",
        "    math.abs(a - b) <= epsilon ? 0 : (a > b ? 1 : -1)",
        "qb_hlc3 = high + ((low - high) + (close - high)) / 3.0",
    ]
    for item in spec.indicators:
        name, kind, n = f"qb_{item.id}", item.kind, item.length
        source: str = "qb_hlc3" if item.source == "hlc3" else item.source
        v = f"{name}_value"
        if kind in {"sma", "stdev"}:
            lines.extend(_pine_window(v, source, n, stdev=kind == "stdev"))
        elif kind == "ema":
            lines.extend(_pine_smooth(v, source, n))
        elif kind == "rsi":
            lines.extend(
                [
                    f"{name}_change = {source} - {source}[1]",
                    f"{name}_gain = math.max({name}_change, 0.0)",
                    f"{name}_loss = math.max(-{name}_change, 0.0)",
                    *_pine_smooth(name + "_avg_gain", name + "_gain", n, rma=True),
                    *_pine_smooth(name + "_avg_loss", name + "_loss", n, rma=True),
                    f"{v} = na({name}_avg_gain) or na({name}_avg_loss) ? na : ({name}_avg_loss == 0 ? 100.0 : 100.0 - 100.0 / (1.0 + {name}_avg_gain / {name}_avg_loss))",
                ]
            )
        elif kind in {"highest", "lowest"}:
            lines.append(f"{v} = ta.{kind}({source}, {n})")
        elif kind == "atr":
            lines.extend(
                [
                    f"{name}_tr = math.max(high - low, math.max(math.abs(high - nz(close[1], close)), math.abs(low - nz(close[1], close))))",
                    *_pine_smooth(v, name + "_tr", n, rma=True),
                ]
            )
        elif kind == "obv":
            lines.extend([f"{v} = ta.obv", *_pine_window(name + "_signal", v, n)])
        elif kind == "macd":
            lines.extend(
                [
                    *_pine_smooth(name + "_fast", source, n),
                    *_pine_smooth(name + "_slow", source, item.slow),
                    f"{v} = {name}_fast - {name}_slow",
                    *_pine_smooth(name + "_signal", v, item.signal),
                ]
            )
        elif kind == "bollinger":
            lines.extend(
                [
                    *_pine_window(v, source, n),
                    *_pine_window(name + "_sd", source, n, stdev=True),
                    f"{name}_upper = {v} + {item.multiplier} * {name}_sd",
                    f"{name}_lower = {v} - {item.multiplier} * {name}_sd",
                ]
            )
        elif kind == "roc":
            lines.append(f"{v} = 100 * ({source} / {source}[{n}] - 1)")
        elif kind in {"stochastic", "williams_r"}:
            lines.extend(
                [
                    f"{name}_hh = ta.highest(high, {n})",
                    f"{name}_ll = ta.lowest(low, {n})",
                    f"{name}_raw = {name}_hh == {name}_ll ? na : 100 * (close - {name}_ll) / ({name}_hh - {name}_ll)",
                ]
            )
            if kind == "williams_r":
                lines.append(f"{v} = {name}_raw - 100")
            else:
                lines.extend(
                    [
                        *_pine_window(v, name + "_raw", item.slow),
                        *_pine_window(name + "_signal", v, item.signal),
                    ]
                )
        elif kind == "donchian":
            lines.extend(
                [
                    f"{name}_upper = ta.highest(high, {n})",
                    f"{name}_lower = ta.lowest(low, {n})",
                    f"{v} = ({name}_upper + {name}_lower) / 2",
                ]
            )
        elif kind in {"keltner", "atr_breakout"}:
            lines.extend(
                [
                    f"{name}_tr = math.max(high - low, math.max(math.abs(high - nz(close[1], close)), math.abs(low - nz(close[1], close))))",
                    *_pine_smooth(name + "_atr", name + "_tr", n, rma=True),
                ]
            )
            if kind == "keltner":
                lines.extend(_pine_smooth(v, source, n))
            else:
                lines.append(f"{v} = close")
            lines.extend(
                [
                    f"{name}_upper = {v} + {item.multiplier} * {name}_atr",
                    f"{name}_lower = {v} - {item.multiplier} * {name}_atr",
                ]
            )
        elif kind == "chandelier":
            lines.extend(
                [
                    f"{name}_tr = math.max(high - low, math.max(math.abs(high - nz(close[1], close)), math.abs(low - nz(close[1], close))))",
                    *_pine_smooth(name + "_atr", name + "_tr", n, rma=True),
                    f"{name}_lower = ta.highest(high, {n}) - {item.multiplier} * {name}_atr",
                    f"{name}_upper = ta.lowest(low, {n}) + {item.multiplier} * {name}_atr",
                ]
            )
        elif kind == "heikin_ashi":
            lines.extend(
                [
                    f"{v} = (open + high + low + close) / 4",
                    f"var float {name}_open = na",
                    f"{name}_open := na({name}_open[1]) ? (open + close) / 2 : ({name}_open[1] + {v}[1]) / 2",
                ]
            )
        elif kind in {"vwap", "anchored_vwap"}:
            lines.extend([f"var float {name}_pv = 0.0", f"var float {name}_vol = 0.0"])
            if kind == "vwap":
                lines.extend(
                    [
                        f"{name}_day = math.floor(time / 86400000)",
                        f"if na({name}_day[1]) or {name}_day != {name}_day[1]",
                        f"    {name}_pv := 0.0",
                        f"    {name}_vol := 0.0",
                    ]
                )
            lines.extend(
                [
                    f"if time >= {item.anchor_ms or 0}",
                    f"    {name}_pv := {name}_pv + qb_hlc3 * volume",
                    f"    {name}_vol := {name}_vol + volume",
                    f"{v} = {name}_vol > 0 ? {name}_pv / {name}_vol : na",
                ]
            )
        elif kind == "cci":
            lines.extend(
                [
                    *_pine_window(name + "_mean", source, n),
                    f"{name}_dev = 0.0",
                    f"for qb_i = 0 to {n - 1}",
                    f"    {name}_dev := {name}_dev + math.abs({_pine_at(source, 'qb_i')} - {name}_mean)",
                    f"{name}_mad = {name}_dev / {n}",
                    f"{v} = na({name}_mean) ? na : ({name}_mad > 0 ? ({source} - {name}_mean) / (0.015 * {name}_mad) : 0.0)",
                ]
            )
        elif kind == "cmf":
            lines.extend(
                [
                    f"{name}_flow = high == low ? 0.0 : ((2 * close - high - low) / (high - low)) * volume",
                    *_pine_window(name + "_volume", "volume", n),
                    *_pine_window(name + "_mean_flow", name + "_flow", n),
                    f"{v} = {name}_volume > 0 ? {name}_mean_flow / {name}_volume : na",
                ]
            )
        elif kind == "mfi":
            lines.extend(
                [
                    f"{name}_positive = qb_hlc3 > qb_hlc3[1] ? qb_hlc3 * volume : 0.0",
                    f"{name}_negative = qb_hlc3 < qb_hlc3[1] ? qb_hlc3 * volume : 0.0",
                    *_pine_window(name + "_pos", name + "_positive", n),
                    *_pine_window(name + "_neg", name + "_negative", n),
                    f"{v} = {name}_neg > 0 ? 100 - 100 / (1 + {name}_pos / {name}_neg) : ({name}_pos > 0 ? 100.0 : na)",
                ]
            )
        elif kind == "aroon":
            lines.extend(
                [
                    f"{name}_hi = high",
                    f"{name}_lo = low",
                    f"{name}_hi_age = 0",
                    f"{name}_lo_age = 0",
                    f"for qb_i = 1 to {n}",
                    f"    if high[qb_i] > {name}_hi",
                    f"        {name}_hi := high[qb_i]",
                    f"        {name}_hi_age := qb_i",
                    f"    if low[qb_i] < {name}_lo",
                    f"        {name}_lo := low[qb_i]",
                    f"        {name}_lo_age := qb_i",
                    f"{name}_up = bar_index >= {n} ? 100.0 * ({n} - {name}_hi_age) / {n} : na",
                    f"{name}_down = bar_index >= {n} ? 100.0 * ({n} - {name}_lo_age) / {n} : na",
                ]
            )
        elif kind == "regression":
            regression_mid = (n - 1) / 2
            den = n * (n * n - 1) / 12
            lines.extend(
                [
                    *_pine_window(name + "_mean", source, n),
                    f"{name}_numerator = 0.0",
                    f"for qb_i = 0 to {n - 1}",
                    f"    {name}_numerator := {name}_numerator + ({n - 1} - qb_i - {regression_mid}) * ({_pine_at(source, 'qb_i')} - {name}_mean)",
                    f"{name}_slope = {name}_numerator / {den}" if den else f"{name}_slope = 0.0",
                    f"{name}_intercept = {name}_mean - {name}_slope * {regression_mid}",
                    f"{v} = {name}_intercept + {name}_slope * {n - 1}",
                    f"{name}_residual = 0.0",
                    f"for qb_i = 0 to {n - 1}",
                    f"    {name}_error = {_pine_at(source, 'qb_i')} - {name}_intercept - {name}_slope * ({n - 1} - qb_i)",
                    f"    {name}_residual := {name}_residual + {name}_error * {name}_error",
                    f"{name}_sd = math.sqrt({name}_residual / {n})",
                    f"{name}_upper = {v} + {item.multiplier} * {name}_sd",
                    f"{name}_lower = {v} - {item.multiplier} * {name}_sd",
                ]
            )
        else:
            raise UnsupportedStrategySpec(f"지원하지 않는 지표: {kind}")
    lines.extend(
        [
            f"qb_long = {_pine_condition(spec.long_entry)}",
            f"qb_short = {_pine_condition(spec.short_entry)}",
            f"qb_ready = bar_index >= {spec.warmup_bars - 1}",
            "qb_can_decide = qb_ready and not (qb_long and qb_short)",
            "qb_enter_long = qb_can_decide and qb_long and strategy.position_size <= 0",
            "qb_enter_short = qb_can_decide and qb_short and strategy.position_size >= 0",
            "qb_close_long = qb_can_decide and strategy.position_size > 0 "
            f"and not qb_enter_short and {_pine_condition(spec.long_invalidation)}",
            "qb_close_short = qb_can_decide and strategy.position_size < 0 "
            f"and not qb_enter_long and {_pine_condition(spec.short_invalidation)}",
            "if qb_enter_long",
            '    strategy.entry("L", strategy.long)',
            "if qb_enter_short",
            '    strategy.entry("S", strategy.short)',
            "if qb_close_long",
            "    strategy.close_all()",
            "if qb_close_short",
            "    strategy.close_all()",
        ]
    )
    return "\n".join(lines) + "\n"


def compile_strategy(spec: StrategySpec | dict[str, Any], language: str) -> str:
    """닫힌 명세를 검증하고, 지원 불가능한 의미는 명시적으로 거부한다."""
    validated = StrategySpec.model_validate(spec)
    unsupported = sorted({item.kind for item in validated.indicators} - SUPPORTED_INDICATORS)
    if unsupported:
        raise UnsupportedStrategySpec("지원하지 않는 지표/패턴: " + ", ".join(unsupported))
    if language == "pine":
        return _compile_pine(validated)
    payload = validated.model_dump(mode="json")
    if language == "python":
        return "_QB_SPEC = " + repr(payload) + "\n" + _PY_RUNTIME
    if language == "typescript":
        return (
            "const _QB_SPEC:any = "
            + json.dumps(payload, ensure_ascii=False, allow_nan=False)
            + ";\n"
            + _TS_RUNTIME
        )
    raise UnsupportedStrategySpec(f"지원하지 않는 언어: {language}")
