var x=function(e,t){var l=this;this.element=t,_.bindAll(this,"xhrProgress"),this.state="queued",this.url=e,this.promise=$.Deferred(),this.promise.request=this,this.promise.cancel=function(){l.state==="active"?l.xhr&&l.xhr.abort():l.state="cancelled"}};x.enableXHR=!0;x.failures=0;x.prototype={doDownload:function(e){var t=this;if(this.state="active",Modernizr.xhrresponsetypeblob&&x.enableXHR&&!e)this.xhr=$.ajax({dataType:"native",url:this.url,xhrFields:{responseType:"blob",onprogress:this.xhrProgress}}),this.startTime=Date.now(),this.promise.notify({loaded:0,total:1}),this.xhr.then(function(o){t.state="complete",t.promise.resolve(o)}),this.xhr.fail(function(o,s){if(s!=="abort"&&!e)return x.failures+=1,x.failures>=5&&(x.enableXHR=!1),t.doDownload(!0);t.state="failed",t.error=o,t.promise.reject(o)});else{this.element.src=this.url;var l=imagesLoaded(this.element,function(){l.images[0].isLoaded?(t.state="complete",t.promise.resolve("fallback")):(t.state="failed",t.promise.reject({fallbackError:"failed"}))})}},xhrProgress:function(e){this.promise.notify(e)}};var B={activeCount:0,active:null,queued:null,requests:{},complete:{},download:function(e,t){var l;if(l=this.requests[e],l){if(l.state==="complete"||l.state==="active")return l.promise;if(l.state==="queued")return this.moveToFront(l),l.promise}return l=new x(e,t),this.requests[e]=l,this.addToFront(l),l.promise},refresh:function(e){var t=e.request;t.state==="queued"&&this.moveToFront(t)},activate:function(e){if(!(this.activeCount>=5)){this.activeCount+=1;var t=this;this.active=this.remove(e),e.doDownload(),e.promise.always(function(){t.activeCount-=1,t.active=null,t.activateNext()}),this.active===this.front&&(this.front=null)}},activateNext:function(){this.queued&&this.activeCount<5&&(this.queued.state==="cancelled"?(this.remove(this.queued),this.activateNext()):this.activate(this.queued))},addToFront:function(e){this.activeCount<5?this.activate(e):this.queued?this.front?(e.next=this.front.next,this.front.next=e,e.prev=this.front,this.front=e,e.next&&(e.next.prev=e)):(e.next=this.queued,this.front=e,this.queued=e,e.next.prev=e):(this.queued=e,this.front=e)},moveToFront:function(e){this.remove(e),this.addToFront(e)},remove:function(e){var t=e.next,l=e.prev;return this.queued===e&&(this.queued=t),this.front===e&&(this.front=t),t&&(t.prev=l),l&&(l.next=t),e.next=null,e.prev=null,e},resetPriority:function(){this.front=null}};const U={scale:1,visible:!1,preload:!1,loader:null,cache:{}};class G{constructor(t){Object.assign(this,U,t)}init(){let t=$("<img></img>").appendTo(this.$el);this.img=t[0];let l=this.size.height/this.size.width,o=$('<div class="aspect-ratio-spacer"></div>').css({"margin-top":l*100+"%"});this.$el.append(o),this.$el.find("img").css({"border-bottom-width":l*5+"px"}).toggleClass("aspect-ratio-wide",l<11/8.5).attr("alt",this.alt),Modernizr.touchevents||this.preloadImage("thumb")}handleVisible(){_.defer(()=>{if(this.visible){let t=this.scale;this.$el.width()>this.size.width||t>2?this.preloadImage("full"):this.$el.width()<250?this.preloadImage("thumb"):this.preloadImage("screen")}})}downloadProgress(t){this.percentLoaded=t.loaded/(t.total||150*1024)*100}preloadImage(t){if(this.loader)if(this.loader.size==t){B.refresh(this.loader);return}else this.loader.cancel();let l=["thumb","screen","full","screen","thumb"],o;for(let i=l.indexOf(t);i<l.length&&(t=l[i],o=this.urls[t],!o);i++);l=["thumb","screen","full"];let s;for(let i=l.indexOf(t);i<l.length&&(s=s||this.cache[l[i]],!s);i++);if(s){this.url=s,this.preloaded=t;return}this.preloaded=null,this.loader=B.download(o,this.img),this.loader.size=t,this.loader.progress(this.downloadProgress).then(i=>{if(i=="fallback")this.cache[t]=this.img.src,this.url=this.img.src,this.preloaded=t,this.loader=null;else{let n=new FileReader;n.readAsDataURL(i),n.onload=()=>{this.cache[t]=n.result,this.url=n.result,this.preloaded=t,this.loader=null}}}).fail(i=>{console.log("preloadImage failed!"),console.dir(this),this.loader=null})}}let T=1,L=null,Z="scoll",X=null,K=null,c=1,d=1,A=null,D=!1,E=null,a=null,g=[],P=null,S=null,m=null,V=null;const k=e=>{g[T-1].$el.removeClass("current"),T=Math.min(Math.max(e,X),K);let t=document.getElementById("page-selector");t.value=T;let l=g[T-1];l.$el.addClass("current"),E=null,z(l)},q=e=>{E=e;let t=$(".viewport-content");(!a||a.$el[0].offsetTop+a.$el[0].offsetHeight>t.scrollTop()+t.height()||a.$el[0].offsetTop<t.scrollTop())&&z(E)},z=e=>{let t=$(".viewport-content"),l=a;e||(a=l),a=e,a.current=!0,l&&(l.current=!1),a!==E&&((t.scrollTop()>a.el.offsetTop||t.scrollTop()+t.height()<a.el.offsetTop+a.el.offsetHeight)&&t.scrollTop(a.el.offsetTop),(t.scrollLeft()>a.el.offsetLeft||t.scrollLeft()+t.width()<a.el.offsetLeft+a.el.offsetWidth)&&t.scrollLeft(a.el.offsetLeft))},F=(e,t)=>{Z=t,e.removeClass("tool-magnify tool-scroll"),e.off("mousewheel",W),e.off("click",w),e.off("contextmenu",w),e.off("dblclick",w),t==="magnify"?(e.addClass("tool-magnify"),e.on("mousewheel",W),e.on("dblclick",w)):(e.addClass("tool-scroll"),e.on("click",w),e.on("contextmenu",w))};let H;const J=e=>{if(D=!D,D){let t=e[0].getBoundingClientRect();H={position:"fixed",left:Math.max(0,t.left),top:Math.max(0,t.top),right:$(window).width()-Math.max(0,t.right),bottom:$(window).height()-Math.max(0,t.bottom),"border-width":0,"border-top-width":0,"background-color":"transparent"},e.css(H),e.addClass("expanded"),e.removeAttr("style"),y()}else e.css(H),setTimeout(()=>{e.removeClass("expanded",D),e.removeAttr("style"),_.defer(y)},300)},R=e=>Math.min(10,Math.max(1,Math.floor(1/(e||c)))),Y=e=>{if($(".viewport-content"),m){let t="setProperty"in m.style?"setProperty":"setAttribute";m.style[t]("font-size",48*e+"px","important"),m.style[t]("line-height",64*e+"px","important"),m.style[t]("height","auto","important"),m.style[t]("width",100*e+"%","important")}},O=(e,t,l)=>{if(e>t)return null;let o=Math.floor((e+t)/2),s=g[o],i={left:s.el.offsetLeft,top:s.el.offsetTop};return i.bottom=i.top+s.el.offsetHeight,i.right=i.left+s.el.offsetWidth,l.top>i.bottom?O(o+1,t,l):l.bottom<i.top?O(e,o-1,l):o},C=(e,t)=>{let l=Math.min(10,Math.max(1,e)),o=$("div.viewport-content");if(d!=l){let s=l/d;L===null&&(L={x:o.scrollLeft(),y:o.scrollTop()});let i={x:Math.max(0,L.x+t.x-t.x/s),y:Math.max(0,L.y+t.y-t.y/s)};d=l,M(d,!0,i)}d=l};let I=null;const M=(e,t,l)=>{let o=$("div.viewport-content"),s=e/(A||1);A=e;let i=300,n={x:l.x*s,y:l.y*s};t?(L=n,$(".document-image-layout").css({width:100*e+"%",left:-n.x+o.scrollLeft()+"px",top:-n.y+o.scrollTop()+"px",margin:"0 100% 100% 0",transition:t?"width "+i+"ms, height "+i+"ms, left "+i+"ms, top "+i+"ms":"none"}),I&&clearTimeout(I),I=setTimeout(function(){I=null,L=null,$(".document-image-layout").css({left:0,top:0,margin:0,"margin-bottom":Math.max(0,n.y+o[0].clientHeight-$(".document-image-layout").height())+"px",transition:"none"}),o.scrollLeft(n.x),o.scrollTop(n.y),y()},i)):$(".document-image-layout").css({width:100*e+"%",left:-n.x+o.scrollLeft()+"px",top:-n.y+o.scrollTop()+"px",transition:"none"})},j=(e,t)=>O(e,e,t)!==null,ee=()=>{let t=$("div.viewport-content");B.resetPriority();let l={top:t.scrollTop(),left:t.scrollLeft()};l.right=l.left+t.width(),l.bottom=l.top+t.height(),l.top-=200,l.bottom+=200;let o=O(0,g.length-1,l),s=o,i=o;for(let r=o-1;r>=0&&j(r,l);r--)s=r;for(let r=o+1;r<P&&j(r,l);r++)i=r;let n;if(Modernizr.touchevents?n=document.body.clientWidth/window.innerWidth:n=c*d,g.forEach((r,f)=>{f>=s&&f<=i?(r.scale=n,r.visible=!0):r.visible=!1}),s!==null){let r=g[s];l.top+=200,l.bottom-=200;let f={top:r.el.offsetTop};f.bottom=f.top=f.top+r.el.offsetHeight/2,f.top>l.bottom?s=Math.max(0,s-R()):f.bottom<l.top&&(s=Math.min(P-1,s+R())),q(g[s])}},y=_.debounce(ee,50),w=e=>{let t=$("div.viewport-content");e.preventDefault();let l={x:e.pageX-t.offset().left,y:e.pageY-t.offset().top},o,s=$(e.target).closest(".document-image"),i;g.forEach((n,r)=>{n.el===s[0]&&(i=n)}),i&&(q(i),z(i)),e.type=="dblclick"?d>=1/c?(o=1,C(o,l)):(d=1/c,M(1/c,!0,{x:i.$el.position().left,y:i.$el.position().top})):(e.which||(e.which=e.keyCode),e.type==="click"&&!e.ctrlKey&&!e.metaKey&&!e.shiftKey?c==1?(o=1.5*d,C(o,l)):(o=1,N(i,o)):(e.type==="contextmenu"||e.ctrlKey||e.metaKey||e.shiftKey)&&(d>1?c<1?(o=1,C(o,l)):(o=1/1.5*d,C(o,l)):(o=1/(R()+1),N(i,o))))},W=e=>{e.preventDefault();let t={x:e.offsetX,y:e.offsetY},l=1+Math.min(1,Math.max(-1,e.deltaY))*.1;C(d*l,t)},N=(e,t)=>{let l=$("div.viewport-content"),o=t/c,s=c,i;c=t;const n=r=>r?{x:r.$el[0].offsetLeft,y:r.$el[0].offsetTop}:{x:l.scrollLeft(),y:l.scrollTop()};if(o<1){if(c<1/P||$(".document-image-layout").height()<=l[0].clientHeight){c=s;return}let r,f,u,h,b;if(e){r=Math.max(0,e.$el.position().top-l.scrollTop()),f=R(s),h=R();let p=parseInt(e.$el.data("page"))-1;u=(p+(i||0))%f,b=p%h,u>=(h-1)/2&&(u=h-(h-1-u)),h>2&&P>3&&(i=(u-b+h)%h,S.css({width:100*c*i+"%"}))}else S.css({width:0});Y(c);let v;e?(v=n(e),u>=(h-1)/2||h==2&&b==1?v.x=l.width()-l.width()*o:e&&(v.x=0),v.y-=r*o):v={x:0,y:0},M(1/o,!1,v),_.defer(function(){M(1,!0,{x:0,y:v.y/o})})}else if(o>1){let r=n(e);M(o,!0,r),setTimeout(()=>{S.css({width:"0%"}),i=0,l.scrollTop(0),l.scrollLeft(0),M(1,!1,{x:0,y:0}),Y(c),e&&(l.scrollTop(e.$el.position().top),l.scrollLeft(e.$el.position().left))},300)}setTimeout(()=>{d=1,y()},300)},te=e=>{e.which!==1||e.which!==3&&Z!=="magnify"||(V={x:e.clientX,y:e.clientY},$(document).on("mousemove",Q),$(document).one("mouseup",le),e.preventDefault())},le=e=>{V=null,$(document).off("mousemove",Q)},Q=e=>{let t=V,l={x:e.clientX,y:e.clientY},o=$("div.viewport-content");o.scrollLeft(o.scrollLeft()+t.x-l.x),o.scrollTop(o.scrollTop()+t.y-l.y),V=l},oe=()=>{let e=document.getElementById("page-selector"),t=e.firstElementChild,l=e.lastElementChild;X=parseInt(t.value),K=parseInt(l.value),$(".first-page").on("click",()=>{k(X)}),$(".last-page").on("click",()=>{k(K)}),$(".next-page").on("click",()=>{k(T+1)}),$(".prev-page").on("click",()=>{k(T-1)}),e.addEventListener("change",()=>{k(parseInt(e.value))});let o=document.querySelector("div.tool-buttons button.magnify"),s=document.querySelector("div.tool-buttons button.scroll"),i=document.querySelector("div.tool-buttons button.expand"),n=$("div.viewport-content");o.addEventListener("click",()=>{F(n,"magnify")}),s.addEventListener("click",()=>{F(n,"scroll")}),i.addEventListener("click",()=>{J(n)});let r=n.find(".document-image");r.each((b,v)=>{let p=$(v);g.push(new G({el:v,$el:p,page:p.data("page"),alt:p.data("alt"),crossorigin:"anonymous",urls:{full:p.data("full-url"),screen:p.data("screen-url"),thumb:p.data("thumb-url")},size:{width:parseInt(p.data("width")),height:parseInt(p.data("height"))}}))}),g.forEach(b=>{b.init()}),n.data("document-id"),P=r.length;let f=n.find(".document-image-layout");Modernizr.touchevents||F(n,"scroll");let u=document.styleSheets[0],h="cssRules"in u?u.cssRules:u.rules;u.insertRule("body.document-viewer #document-viewport .document-image { width: 100% !important; height: auto !important; }",0),m=h[0],m&&m.cssRules&&(m=m.cssRules[0]),S=$("<div></div>").css({display:"inline-block",width:0,height:"1px"}).prependTo(f),n.on("scroll",()=>{y()}),n.on("resize",()=>{y()}),n.on("mousedown",te),y(),q(g[0])};document.addEventListener("DOMContentLoaded",oe);
