import{c}from"./popper-c02d395e.js";const d=["mouseenter","focus"],r=["mouseleave","blur"],l=e=>{Array.from(e).forEach(t=>{const s=t.dataset.content_id,o=document.getElementById(s),a=c(t,o,{placement:"left",modifiers:[{name:"offset",options:{offset:[0,-100]}}]});d.forEach(n=>{t.addEventListener(n,()=>{o.setAttribute("data-show",""),a.update()})}),r.forEach(n=>{t.addEventListener(n,()=>{o.removeAttribute("data-show")})})})},m=()=>{const e=document.getElementsByClassName("help-label");console.dir(e),l(e),console.log("advancedSearch.js")};document.addEventListener("DOMContentLoaded",m);
