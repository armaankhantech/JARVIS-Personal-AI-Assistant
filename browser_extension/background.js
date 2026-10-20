importScripts('config.js');
const BASE='http://127.0.0.1:31419';
const headers={'Content-Type':'application/json','X-Jarvis-Token':JARVIS_BRIDGE_TOKEN};
async function bridge(path,options={}){const r=await fetch(BASE+path,{...options,headers:{...headers,...(options.headers||{})}});return await r.json();}
async function ensureOffscreen(){const url=chrome.runtime.getURL('offscreen.html');const contexts=await chrome.runtime.getContexts({contextTypes:['OFFSCREEN_DOCUMENT'],documentUrls:[url]});if(!contexts.length)await chrome.offscreen.createDocument({url:'offscreen.html',reasons:['BLOBS'],justification:'Poll the local Jarvis bridge for browser commands.'});}
chrome.runtime.onInstalled.addListener(()=>ensureOffscreen().catch(()=>{}));
chrome.runtime.onStartup.addListener(()=>ensureOffscreen().catch(()=>{}));
chrome.runtime.onMessage.addListener((msg,sender,sendResponse)=>{if(msg?.type==='JARVIS_COMMAND'){execute(msg.command).then(async result=>{try{await bridge('/result',{method:'POST',body:JSON.stringify({id:msg.command.id,result})});sendResponse({success:true});}catch(e){sendResponse({success:false,error:String(e)});}}).catch(e=>sendResponse({success:false,error:String(e)}));return true;} if(msg?.type==='JARVIS_BRIDGE_STATUS'){sendResponse({success:true,tokenConfigured:true});}});
async function navigateAndWait(tabId, url) {
  let listener;
  let timer;

  const completed = new Promise((resolve, reject) => {
    listener = (updatedId, changeInfo, updatedTab) => {
      if (updatedId === tabId && changeInfo.status === 'complete') {
        clearTimeout(timer);
        chrome.tabs.onUpdated.removeListener(listener);
        resolve(updatedTab);
      }
    };

    chrome.tabs.onUpdated.addListener(listener);

    timer = setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(listener);
      reject(new Error('Navigation timed out after 15 seconds'));
    }, 15000);
  });

  try {
    await chrome.tabs.update(tabId, {url});
    return await completed;
  } catch (error) {
    clearTimeout(timer);
    chrome.tabs.onUpdated.removeListener(listener);
    throw error;
  }
}
async function execute(command){const {action,args={}}=command;if(action==='tabs'){const tabs=await chrome.tabs.query({});return {success:true,tabs:tabs.map(t=>({id:t.id,title:t.title,url:t.url,active:t.active,windowId:t.windowId}))};}let tab;if(Number.isInteger(args.tab_id))tab=await chrome.tabs.get(args.tab_id);else{const [t]=await chrome.tabs.query({active:true,lastFocusedWindow:true});tab=t;}if(action==='active_tab')return tab?{success:true,tab:{id:tab.id,title:tab.title,url:tab.url,windowId:tab.windowId}}:{success:false,error:'No active tab'};if(action==='navigate'){if(!tab)return {success:false,error:'No target tab'};const url=String(args.url||'');if(!/^https?:\/\//i.test(url))return {success:false,error:'Only http/https URLs are allowed'};const finalTab = await navigateAndWait(tab.id, url);
return {success:true,tabId:tab.id,url:finalTab.url};}if(['click','fill','press','read','find_click','find_fill','click_first_video','video_seek'].includes(action)){if(!tab?.id)return {success:false,error:'No target tab'};try{return await chrome.tabs.sendMessage(tab.id,{action,args});}catch(e){return {success:false,error:'Page cannot be controlled; refresh the page. Chrome internal pages are not controllable.'};}}return {success:false,error:'Unsupported action'};}
