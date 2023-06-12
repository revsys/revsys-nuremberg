$(".clear-search").on("click",function(t){t.preventDefault(),$(this).closest("form").find('input[type="search"]').val("")});let i=$(".viewport-content"),r=i.find(".transcript-text"),o=r.data("seq"),v,q;r.data("page-count");let g=r.data("total-pages"),d=r.data("from-seq"),f=r.data("to-seq"),u=$("input[name=q]").val(),C=10;$(".print-document").on("click",function(){$(".print-options, .print-document").toggleClass("hide")});$(".do-print").on("click",function(t){t.preventDefault();var e=parseInt($(".print-options input[name=pages]").val());if(e>20||e<1)return e=Math.min(Math.max(e,1),20),$(".print-options input[name=pages]").val(e);var a=o+e-f;if(a>1)var n=x(Math.ceil(a/10));n?n.then(function(){k(e)}):k(e)});const y=t=>t.toString().replace(/\B(?=(\d{3})+(?!\d))/g,","),k=t=>{let e=$(".page").addClass("print-hide"),a=[0,0],n=[0,0],l=0;for(let p=o;p<=o+t-1;p++){let h=e.filter('[data-seq="'+p+'"]');h.removeClass("print-hide"),h.length&&(a[0]=a[0]||h.data("page")||"?",a[1]=h.data("page")||"?",n[0]=n[0]||h.data("seq"),n[1]=h.data("seq"),l+=1)}$(".document-info .print-show").text("Printed "+l+" transcript pages labeled "+_.map(a,y).join(" through ")+" (seq. nos. "+n.join("-")+")"),$(".print-options, .print-document").toggleClass("hide"),window.print(),e.removeClass("print-hide")},c=t=>{o=Math.min(Math.max(t,1),g);let e=i.find('.page[data-seq="'+o+'"]');e.length&&(i.scrollTop(e[0].offsetTop-10),history&&history.replaceState&&history.replaceState(void 0,void 0,location.pathname+location.search.replace(/seq=\d+/,"seq="+t)))},D=t=>{var e=$('.page[data-page="'+t+'"]');return e.length?(c(e.data("seq")),!0):!1},M=t=>{var e=$('.page[data-date="'+t+'"]');return e.length?(c(e.data("seq")),!0):!1};var S=o;c(S);setTimeout(function(){c(S)},100);$(".page-buttons .next-page").on("click",function(){c(o+1)});$(".page-buttons .prev-page").on("click",function(){c(o-1)});$(".page-buttons .first-page").on("click",function(){d<=1?c(1):m({seq:1})});$(".page-buttons .last-page").on("click",function(){d>=g?c(1):m({seq:g})});$("form.go-to-page").on("submit",function(t){t.preventDefault();var e=$(this).find("input[name=page]"),a=e.val();if(a<1)return e.val(1);if(a>g)return e.val(g);$('.page[data-page="'+a+'"]'),D(a)||m({page:a})});$("select.select-date").on("change",function(){var t=$(this).val();M(t)||m({date:t})});const w=(t,e)=>{if(t.find("mark").contents().unwrap(),!e)return;e=e.replace(/evidence:|exhibit:/,"").replace(/((?:\-?\w+)\s*\:\s*(?:"[^"]+"|\([^:]+\)|[\w\-\+\.\|]+))/,"");let a=e.match(/"([^"]+)"/g);a=_.map(a,function(l){return l.replace(/^"|"$/g,"").replace(/[^\w]+/g,"[^\\w]+")}),e=e.replace(/"([^"]+)"/g,"");let n=e.replace(/[^\w\-]+/g," ").replace(/^\s+|\s+$/g,"").replace(/(s|ing|ed|ment)\b/g,"").split(/\ +/g);n=_.reject(n,function(l){return!l||l.length<3&&!l.match(/[A-Z]{2,3}|\d+/)}),n=n.concat(a),n.length&&new RegExp("\\b("+n.join("|")+")(s|ing|ed|ment)?\\b","ig")},b=()=>{r.html(w(r,u))};b();$("input[name=q]").on("keyup",_.debounce(function(){u=this.value,b()},500));$(".clear-search").on("click",function(t){t.preventDefault(),$(this).closest("form").find('input[type="search"]').val("").trigger("keyup")});let s=!1;const x=t=>{if(t=t||1,f>=g){i.find(".below .end-indicator").text("End of transcript");return}else i.find(".below .end-indicator").text("Loading...");if(!s)return s=!0,$.get({url:location.pathname,data:{from_seq:f,to_seq:Math.min(g,f+t*C+1),partial:!0}}).then(function(e){f=e.to_seq;var a=$("<div></div>");a.append($(e.html)),w(a,u),r.append(a),s=!1})},T=()=>{if(d<=1){i.find(".above .end-indicator").text("Beginning of transcript");return}else i.find(".above .end-indicator").text("Loading...");s||(s=!0,$.get({url:location.pathname,data:{from_seq:Math.max(1,d-(C+1)),to_seq:d,partial:!0}}).then(function(t){d=t.from_seq;var e=$("<div></div>");e.append($(t.html)),w(e,u),r.prepend(e),i.scrollTop(i.scrollTop()+e.height()+29),s=!1}))},m=t=>{s||(t.partial=!0,t.seq=t.seq||o,s=!0,r.empty(),$.get({url:location.pathname,data:t}).then(function(e){d=e.from_seq,f=e.to_seq,r.append(e.html),b(),e.seq&&c(e.seq),s=!1}))};d<=1&&T();f>=g&&x();i.on("click","a.view-image",t=>{var e=$(globalThis).closest(".page-handle"),a=e.find(".download-image").attr("href");e.hasClass("has-image")||e.addClass("has-image").after('<div class="page-image hide"><img src="'+a+'" /></div>'),$img=e.next(".page-image"),$img.toggleClass("hide"),$img.hasClass("hide")?(e.removeClass("show"),e.find("a.view-image").text("VIEW")):(e.addClass("show"),e.find("a.view-image").text("HIDE")),t.stopPropagation()});i.on("click",".page-handle",()=>{$(globalThis).addClass("show")});const P=()=>{let t={top:i.scrollTop(),height:i.height()*2,bottom:i.scrollTop()+i.height()},e={top:0,bottom:i[0].scrollHeight};t.bottom+t.height>e.bottom?x():t.top-t.height<e.top&&T();let a=i[0].getBoundingClientRect(),n={x:a.left+100,y:a.top+10};do{if(n.y+=100,n.y>a.top+1e3)return;var l=document.elementFromPoint(n.x,n.y),p=$(l).closest(".page")}while(p.length==0);o=p.data("seq"),q=p.data("page"),v=p.data("date"),o&&history&&history.replaceState&&history.replaceState(void 0,void 0,location.pathname+location.search.replace(/seq=\d+/,"seq="+o)),v&&$("select.select-date").val(v),q&&$("form.go-to-page input[name=page]").val(q)};i.on("scroll",_.throttle(P,300));
