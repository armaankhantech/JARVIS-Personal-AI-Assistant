chrome.runtime.onMessage.addListener((message,sender,sendResponse)=>{const {action,args={}}=message||{};const selector=String(args.selector||'');const query=()=>{if(!selector)throw new Error('A CSS selector is required');const el=document.querySelector(selector);if(!el)throw new Error('Element not found: '+selector);return el;};try{if(action==='read'){const el=selector?query():document.body;sendResponse({success:true,url:location.href,title:document.title,text:(el.innerText||el.textContent||'').slice(0,12000)});}else if(action==='click'){const el=query();el.click();sendResponse({success:true,clicked:selector,url:location.href});}else if(action==='fill'){const el=query();el.focus();const value=String(args.text??'');if(el.isContentEditable)el.textContent=value;else{const proto=el instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:el instanceof HTMLInputElement?HTMLInputElement.prototype:Object.getPrototypeOf(el);const setter=Object.getOwnPropertyDescriptor(proto,'value')?.set;if(setter)setter.call(el,value);else el.value=value;}el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));sendResponse({success:true,filled:selector});}else if(action==='press'){const el=selector?query():document.activeElement;if(!el)throw new Error('No focused element');const key=String(args.key||'Enter');el.dispatchEvent(new KeyboardEvent('keydown',{key,bubbles:true}));el.dispatchEvent(new KeyboardEvent('keyup',{key,bubbles:true}));if(key==='Enter'&&el.form)el.form.requestSubmit();sendResponse({success:true,pressed:key,selector:selector||'(active element)'});}else if(action==='find_click'){const text=String(args.text||'').trim();if(!text)throw new Error('Text is required');const el=[...document.querySelectorAll('a,button,[role="button"],input[type="submit"]')].find(e=>(e.innerText||e.getAttribute('aria-label')||e.value||'').trim().toLowerCase().includes(text.toLowerCase()));if(!el)throw new Error('No clickable element matching text: '+text);el.click();sendResponse({success:true,clicked_text:(el.innerText||el.getAttribute('aria-label')||el.value||'').trim(),url:location.href});}else if(action==='find_fill'){
const wanted=String(args.label||'').trim().toLowerCase();
const value=String(args.text??'');
if(!wanted)throw new Error('A field label is required');
const visible=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none'&&!e.disabled;};
const fields=[...document.querySelectorAll('input:not([type=hidden]),textarea,[contenteditable="true"],[role="textbox"]')].filter(visible);
const describe=e=>{
const id=e.id;
const label=id?[...document.querySelectorAll('label[for]')].find(l=>l.htmlFor===id)?.innerText:'';
return [e.getAttribute('placeholder'),e.getAttribute('aria-label'),e.getAttribute('name'),e.getAttribute('title'),label,e.getAttribute('data-placeholder')].filter(Boolean).join(' ').toLowerCase();
};
fields.sort((a,b)=>{
const score=e=>{const d=describe(e);return d.trim()===wanted?3:d.includes(wanted)?2:0;};
return score(b)-score(a);
});
const el=fields.find(e=>describe(e).includes(wanted));
if(!el)throw new Error('No visible input matched label: '+wanted);
el.focus();
if(el.isContentEditable)el.textContent=value;
else{
const proto=el instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:el instanceof HTMLInputElement?HTMLInputElement.prototype:Object.getPrototypeOf(el);
const setter=Object.getOwnPropertyDescriptor(proto,'value')?.set;
if(setter)setter.call(el,value);else el.value=value;
}
el.dispatchEvent(new Event('input',{bubbles:true}));
el.dispatchEvent(new Event('change',{bubbles:true}));
sendResponse({success:true,filled:true,field:wanted,value,url:location.href});
}else if(action==='click_first_video'){
if(location.hostname!=='youtube.com'&&!location.hostname.endsWith('.youtube.com'))throw new Error('This action only works on YouTube');
const visible=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none';};
const links=[...document.querySelectorAll('ytd-video-renderer a#video-title,ytd-rich-item-renderer a#video-title,a#video-title[href*="/watch"]')].filter(e=>visible(e)&&e.href.includes('/watch'));
const el=links[0];
if(!el)throw new Error('No visible YouTube video result found. Search for videos first.');
const title=(el.innerText||el.getAttribute('title')||'').trim();
const url=el.href;
el.click();
sendResponse({success:true,clicked:true,title,url});
}else if(action==='video_seek'){const video=document.querySelector('video');if(!video)throw new Error('No HTML video on this page');const before=video.currentTime;const duration=Number.isFinite(video.duration)?video.duration:null;const target=Math.max(0,Math.min(duration??Infinity,before+Number(args.seconds||0)));video.currentTime=target;sendResponse({success:true,position_before:before,position_after:video.currentTime,duration,verified:Math.abs(video.currentTime-target)<1,url:location.href});}else sendResponse({success:false,error:'Unsupported action'});}catch(e){sendResponse({success:false,error:String(e)});}return true;});
