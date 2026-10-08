from pathlib import Path
import os, tempfile
from playwright.sync_api import sync_playwright
from browser_runtime import resolve_chromium_executable
import json, re, sys

ROOT=Path(__file__).resolve().parents[1]
WWW=ROOT/'src'/'ControlWeb'/'www'
_shot_override = os.environ.get('CONTROL_SCREENSHOT_DIR')

if _shot_override:
    SHOT = Path(_shot_override).expanduser().resolve()
    _SHOT_TMP = None
else:
    _SHOT_TMP = tempfile.TemporaryDirectory(
        prefix='asf-control-suite-ui-'
    )
    SHOT = Path(_SHOT_TMP.name)

SHOT.mkdir(parents=True, exist_ok=True)
index=(WWW/'index.html').read_text(encoding='utf-8')
css=(WWW/'app.css').read_text(encoding='utf-8')
core=(WWW/'core.js').read_text(encoding='utf-8')
i18n=(WWW/'i18n.js').read_text(encoding='utf-8')
qrcode=(WWW/'qrcode.min.js').read_text(encoding='utf-8') if (WWW/'qrcode.min.js').exists() else ''
app=(WWW/'app.js').read_text(encoding='utf-8')
# Production CSP is checked by static_contracts.py. Inline only in this networkless harness.
index=re.sub(r'\s*<meta http-equiv="Content-Security-Policy"[^>]*>\s*','\n',index,count=1)

mock=r'''(() => {
 const mem=new Map(); Object.defineProperty(window,'sessionStorage',{configurable:true,value:{getItem:k=>mem.has(k)?mem.get(k):null,setItem:(k,v)=>mem.set(k,String(v)),removeItem:k=>mem.delete(k)}});
 const localMem=new Map([['asf-ui:locale','\"en-US\"']]); Object.defineProperty(window,'localStorage',{configurable:true,value:{getItem:k=>localMem.has(k)?localMem.get(k):null,setItem:(k,v)=>localMem.set(k,String(v)),removeItem:k=>localMem.delete(k)}});
 const lib=[
  {AppId:10,Name:'Owned Game',Source:'own',CanSelect:true,Available:true,CurrentHours:1,FamilyAvailabilityKnown:true},
  {AppId:11,Name:'Family Game',Source:'family',CanSelect:true,Available:true,CurrentHours:.5,FamilyAvailabilityKnown:true},
  {AppId:20,Name:'Free Game',Source:'free',CanSelect:true,Available:true,CurrentHours:0,FamilyAvailabilityKnown:true},
  {AppId:30,Name:'Excluded Managed',Source:'excluded',CanSelect:false,Available:false,CurrentHours:.25,FamilyAvailabilityKnown:true},
  {AppId:40,Name:'Excluded New',Source:'excluded',CanSelect:false,Available:false,CurrentHours:0,FamilyAvailabilityKnown:true},
  {AppId:50,Name:'12 is Better Than 6',Source:'own',CanSelect:true,Available:true,CurrentHours:.1,FamilyAvailabilityKnown:true},
  {AppId:60,Name:'8AM',Source:'own',CanSelect:true,Available:true,CurrentHours:.2,FamilyAvailabilityKnown:true}
 ];
 window.__m={
  accounts:[{BotName:'main',Nickname:'Mock Main',SteamId:'mock',AvatarHash:'abc123',QrChallengeUrl:null,Enabled:true,KeepRunning:true,Connected:true,IsPlayingPossible:true,Farming:false,FarmerPaused:false,HasMobileAuthenticator:true,RequiredInput:1}],
  defaults:{OnlineStatus:1},
  configs:{main:{Enabled:true,OnlineStatus:1,SteamTradeToken:'SECRET-TOKEN',GamesPlayedWhileIdle:[999],CustomGamePlayedWhileIdle:'legacy',OtherPluginSetting:{KeepMe:true},PlaytimeGoalsEnabled:true,PlaytimeGoalsBatchSize:2,PlaytimeGoalsParentalWritesEnabled:false,PlaytimeGoals:{'10':2,'30':5}}},
  inputs:[],actions:[],restart:0,exit:0,libraryReads:0,accountReads:0,qrInputCounts:{},
  globalConfig:{Headless:true,IPC:true,UpdateChannel:0,IPCPassword:'GLOBAL-SECRET',LicenseID:'11111111-2222-3333-4444-555555555555',WebProxyPassword:'PROXY-SECRET'},
  plugins:[{Name:'PlaytimeGoals',Version:'0.5.2.0'},{Name:'ControlWeb',Version:'1.0.0.0'}],
  bans:['203.0.113.5'],
  bgr:{main:{UsedKeys:{},UnusedKeys:{}}},
  commands:[],confirmations:{main:[{Type:2,s_CreatorID:'42',s_ID:'7'}]},authenticatorOps:[],bgrReads:0,
  licenseOps:[],redeemOps:[],inventoryReads:0,pointsOps:[],
  ptgUnavailable:false,ptgSnapshot:null
 };
 const env=(Result=null,Success=true,Message=null)=>({Success,Message,Result});
 const resp=(p,s=200)=>({ok:s>=200&&s<300,status:s,statusText:s===200?'OK':'ERR',json:async()=>p});
 const ptg=bot=>{const c=window.__m.configs[bot],goals=c.PlaytimeGoals||{},by=Object.fromEntries(lib.map(g=>[String(g.AppId),g])); return {Bot:bot,Enabled:!!c.PlaytimeGoalsEnabled,ParentalWritesEnabled:!!c.PlaytimeGoalsParentalWritesEnabled,BatchSize:c.PlaytimeGoalsBatchSize||5,Connected:true,Farming:false,FarmerPaused:false,PlayingPossible:true,RecoveryReady:true,CurrentBatch:Object.keys(goals).slice(0,1).map(Number),Games:Object.entries(goals).map(([id,t],i)=>{const currentHours=by[id]?.CurrentHours||0,currentSeconds=Math.round(currentHours*3600),targetSeconds=t==null?null:Math.ceil(t*3600),remainingSeconds=targetSeconds==null?null:Math.max(0,targetSeconds-currentSeconds);return {AppId:Number(id),Name:by[id]?.Name||id,TargetHours:t,TargetSeconds:targetSeconds,CurrentHours:currentHours,CurrentSeconds:currentSeconds,EffectiveHours:currentHours,EffectiveSeconds:currentSeconds,RemainingHours:remainingSeconds==null?null:remainingSeconds/3600,RemainingSeconds:remainingSeconds,State:'queued',QueuePosition:i+1};})}};
 window.fetch=async(path,opt={})=>{
  path=String(path); const method=String(opt.method||'GET').toUpperCase(),auth=opt.headers?.get?.('Authentication');
  if(path.startsWith('/Api/')&&auth!=='secret')return resp(env(null,false,'unauthorized'),401);
  const body=opt.body?JSON.parse(opt.body):null;
  if(method==='GET'&&path==='/Api/ASF')return resp(env({Version:'6.3.10.3',BuildVariant:'linux-arm64',MemoryUsage:8192,GlobalConfig:window.__m.globalConfig}));
  if(method==='POST'&&path==='/Api/ASF'){const old=window.__m.globalConfig;window.__m.globalConfig={...body.GlobalConfig,IPCPassword:old.IPCPassword,LicenseID:old.LicenseID,WebProxyPassword:old.WebProxyPassword};return resp(env(null));}
  if(method==='GET'&&path==='/Api/AccountManager'){window.__m.accountReads++;return resp(env({Accounts:window.__m.accounts}));}
  if(method==='GET'&&path==='/Api/AccountManager/Defaults')return resp(env({Defaults:window.__m.defaults,ForbiddenKeys:['SteamPassword','SteamLogin'],MaxPayloadChars:65536}));
  if(method==='POST'&&path==='/Api/AccountManager/Defaults'){window.__m.defaults=body;return resp(env({Defaults:body}));}
  if(method==='GET'&&path==='/Api/ControlCenter/Status')return resp(env({UptimeSeconds:3720,ControlSuiteVersion:'9.8.7',ControlModuleVersion:'9.8.7.6',TargetAsfVersion:'test-asf-version',TargetAsfCommit:'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',TargetAsfUiCommit:'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',TargetPlaytimeGoalsVersion:'0.5.9.0',TargetPlaytimeGoalsCommit:'cccccccccccccccccccccccccccccccccccccccc',ManagedMemoryKiB:2048,ProcessWorkingSetKiB:4096,ProcessorCount:8,StorageAvailable:true,DiskFreeBytes:40*1024**3,DiskTotalBytes:64*1024**3,WaitingForInputBots:window.__m.accounts.filter(a=>a.RequiredInput).length,Framework:'.NET 10 mock',OS:'Mock Linux',ProcessArchitecture:'Arm64',Modules:[{Name:'PlaytimeGoals',Loaded:true,Version:'0.5.1.0',ExpectedVersion:'0.5.1.0'},{Name:'AccountManager',Loaded:true,Version:'1.0.0.0',ExpectedVersion:'1.0.0.0'},{Name:'ControlCenter',Loaded:true,Version:'1.0.0.0',ExpectedVersion:'1.0.0.0'},{Name:'ControlWeb',Loaded:true,Version:'1.0.0.0',ExpectedVersion:'1.0.0.0'}]}));
  if(method==='POST'&&path==='/Api/ASF/Encrypt')return resp(env('AES-CIPHERTEXT'));
  if(method==='POST'&&path==='/Api/ASF/Hash')return resp(env('HASHED-VALUE'));
  if(method==='POST'&&path==='/Api/ASF/Restart'){window.__m.restart++;return resp(env(null));}
  if(method==='POST'&&path==='/Api/ASF/Exit'){window.__m.exit++;return resp(env(null));}
  if(method==='GET'&&path==='/Api/Plugins')return resp(env(window.__m.plugins));
  if(method==='GET'&&path==='/Api/IPC/Bans')return resp(env(window.__m.bans));
  if(method==='GET'&&path.startsWith('/Api/NLog/File'))return resp(env({Content:['mock log line 1','mock log line 2'],TotalLines:2}));
  if(method==='DELETE'&&path==='/Api/IPC/Bans'){window.__m.bans=[];return resp(env(null));}
  let ban=path.match(/^\/Api\/IPC\/Bans\/(.+)$/);
  if(method==='DELETE'&&ban){const ip=decodeURIComponent(ban[1]);window.__m.bans=window.__m.bans.filter(x=>x!==ip);return resp(env(null));}
  if(method==='POST'&&path==='/Api/Command'){window.__m.commands.push(body.Command);return resp(env('OK '+body.Command));}
  let addLicense=path.match(/^\/Api\/Bot\/([^/]+)\/AddLicense$/);
  if(method==='POST'&&addLicense){const bot=decodeURIComponent(addLicense[1]);window.__m.licenseOps.push(['add',bot,body]);return resp(env({[bot]:env({Apps:body.Apps||[],Packages:body.Packages||[]})}));}
  let removeLicense=path.match(/^\/Api\/Bot\/([^/]+)\/RemoveLicense$/);
  if(method==='POST'&&removeLicense){const bot=decodeURIComponent(removeLicense[1]);window.__m.licenseOps.push(['remove',bot,body]);return resp(env({[bot]:env(null)}));}
  let redeem=path.match(/^\/Api\/Bot\/([^/]+)\/Redeem$/);
  if(method==='POST'&&redeem){const bot=decodeURIComponent(redeem[1]);window.__m.redeemOps.push([bot,body]);return resp(env({[bot]:env({Results:Object.fromEntries((body.KeysToRedeem||[]).map(key=>[key,'OK']))})}));}
  let inventory=path.match(/^\/Api\/Bot\/([^/]+)\/Inventory$/);
  if(method==='GET'&&inventory){const bot=decodeURIComponent(inventory[1]);window.__m.inventoryReads++;return resp(env({[bot]:env({730:[2,6],753:[6]})}));}
  let inventoryItems=path.match(/^\/Api\/Bot\/([^/]+)\/Inventory\/(\d+)\/(\d+)(?:\?language=([^&]+))?$/);
  if(method==='GET'&&inventoryItems){const bot=decodeURIComponent(inventoryItems[1]),app=Number(inventoryItems[2]),context=Number(inventoryItems[3]),language=inventoryItems[4]?decodeURIComponent(inventoryItems[4]):null;window.__m.inventoryReads++;return resp(env({[bot]:env({AppID:app,ContextID:context,Language:language,Items:[{AssetID:'1'}]})}));}
  let redeemPoints=path.match(/^\/Api\/Bot\/([^/]+)\/RedeemPoints\/(\d+)(?:\?.*)?$/);
  if(method==='POST'&&redeemPoints){const bot=decodeURIComponent(redeemPoints[1]);const definition=Number(redeemPoints[2]);window.__m.pointsOps.push([bot,definition,path.includes('forced=true')]);return resp(env({[bot]:env(true)}));}
  let nativeBgr=path.match(/^\/Api\/Bot\/([^/]+)\/GamesToRedeemInBackground$/);
  if(nativeBgr){const bot=decodeURIComponent(nativeBgr[1]);window.__m.bgr[bot]??={UsedKeys:{},UnusedKeys:{}};if(method==='GET'){window.__m.bgrReads++;return resp(env({[bot]:window.__m.bgr[bot]}));}if(method==='POST'){window.__m.bgr[bot].UnusedKeys={...window.__m.bgr[bot].UnusedKeys,...body.GamesToRedeemInBackground};return resp(env({[bot]:body.GamesToRedeemInBackground}));}}
  let tokenPath=path.match(/^\/Api\/Bot\/([^/]+)\/TwoFactorAuthentication\/Token$/);
  if(method==='GET'&&tokenPath){const bot=decodeURIComponent(tokenPath[1]);return resp(env({[bot]:env('12345')}));}
  let confirmationsPath=path.match(/^\/Api\/Bot\/([^/]+)\/TwoFactorAuthentication\/Confirmations$/);
  if(confirmationsPath){const bot=decodeURIComponent(confirmationsPath[1]);if(method==='GET')return resp(env({[bot]:env(window.__m.confirmations[bot]||[])}));if(method==='POST'){window.__m.confirmations[bot]=[];return resp(env({[bot]:env([])}));}}
  let authenticatorPath=path.match(/^\/Api\/Bot\/([^/]+)\/TwoFactorAuthentication$/);
  if(authenticatorPath){const bot=decodeURIComponent(authenticatorPath[1]);if(method==='POST'){window.__m.authenticatorOps.push(['import',bot,body]);return resp(env({[bot]:env(null)}));}if(method==='DELETE'){window.__m.authenticatorOps.push(['delete',bot]);return resp(env({[bot]:env(null)}));}}
  let m=path.match(/^\/Api\/PlaytimeGoals\/([^/]+)(?:\/(Library|Parental))?$/);
  if(method==='GET'&&m){let bot=decodeURIComponent(m[1]); if(!m[2]){if(window.__m.ptgUnavailable)return resp(env(null,false,'unavailable'),503);return resp(env(window.__m.ptgSnapshot??ptg(bot)));} if(m[2]==='Library'){window.__m.libraryReads++;return resp(env({FamilyMemberCount:4,Games:lib}));} return resp(env({Available:true,Enabled:true,BaseListId:1,BaseEntryCount:2,CustomEntryCount:1,Apps:[{AppId:10,BaseAllowed:true,CustomAllowed:null,EffectiveAllowed:true},{AppId:30,BaseAllowed:false,CustomAllowed:true,EffectiveAllowed:true}]}));}
  m=path.match(/^\/Api\/Bot\/([^/]+)(?:\/(Start|Stop|Pause|Resume|Rename|Input))?$/);
  if(m){
   let bot=decodeURIComponent(m[1]),act=m[2]||null;
   if(method==='GET'&&!act)return resp(env({[bot]:{BotConfig:window.__m.configs[bot]}}));
   if(method==='POST'&&act==='Input'){window.__m.inputs.push([bot,body]);const a=window.__m.accounts.find(a=>a.BotName===bot);if(body.Type===8&&body.Value==='Y'){window.__m.qrInputCounts[bot]=(window.__m.qrInputCounts[bot]||0)+1;a.RequiredInput=8;a.QrChallengeUrl=window.__m.qrInputCounts[bot]===1?'https://s.team/q/TEST-ONE':'https://s.team/q/TEST-RETRY';}else a.RequiredInput=0;return resp(env(null));}
   if(method==='POST'&&act==='Rename'){const next=body.NewName; const a=window.__m.accounts.find(x=>x.BotName===bot); if(a)a.BotName=next; window.__m.configs[next]=window.__m.configs[bot]; delete window.__m.configs[bot]; return resp(env(null));}
   if(method==='POST'&&act){window.__m.actions.push([bot,act]);const a=window.__m.accounts.find(x=>x.BotName===bot); if(a){if(act==='Start')a.KeepRunning=true;if(act==='Stop')a.KeepRunning=false;if(act==='Pause')a.FarmerPaused=true;if(act==='Resume')a.FarmerPaused=false;}return resp(env(null));}
   if(method==='POST'&&!act){let cfg=body.BotConfig;window.__m.configs[bot]=cfg;let a=window.__m.accounts.find(x=>x.BotName===bot); if(!a){window.__m.accounts.push({BotName:bot,Nickname:'',SteamId:'0',AvatarHash:null,QrChallengeUrl:null,Enabled:!!cfg.Enabled,KeepRunning:true,Connected:false,IsPlayingPossible:true,Farming:false,FarmerPaused:false,HasMobileAuthenticator:false,RequiredInput:(!cfg.SteamLogin&&!cfg.SteamPassword)?8:0});} else a.Enabled=!!cfg.Enabled;return resp(env({[bot]:true}));}
   if(method==='DELETE'){window.__m.accounts=window.__m.accounts.filter(x=>x.BotName!==bot);delete window.__m.configs[bot];return resp(env(null));}
  }
  return resp(env(null,false,'not found'),404);
 };
})();'''

html=index.replace('<link rel="stylesheet" href="/Control/app.css">',f'<style>{css}</style>').replace('<script src="/Control/i18n.js"></script>',f'<script>{mock}</script><script>{i18n}</script>').replace('<script src="/Control/core.js"></script>',f'<script>{core}</script>').replace('<script src="/Control/qrcode.min.js"></script>',f'<script>{qrcode}</script>').replace('<script src="/Control/app.js" defer></script>',f'<script>{app}</script>')
html_uk=html.replace("[['asf-ui:locale','\\\"en-US\\\"']]", "[['asf-ui:locale','\\\"uk-UA\\\"']]")
html_uk_alias=html.replace("[['asf-ui:locale','\\\"en-US\\\"']]", "[['asf-ui:locale','\\\"uk\\\"']]")
html_legacy_auth=html.replace(
   'const mem=new Map();',
   "const mem=new Map([['asf.control.view','dashboard'],['asf.control.lockMinutes','30'],['asf.control.ipcPassword','legacy-secret']]);",
   1
)

def login(page):
    page.fill('#password','secret')
    page.click('#authForm button[type="submit"]')
    page.wait_for_selector('#app:not(.hidden)')
    page.wait_for_selector('#content .card')

def assert_accessible_controls(page):
    unnamed=page.evaluate('''() => [...document.querySelectorAll('button,input,select,textarea')].filter(el=>{
      if(el.disabled || el.type==='hidden') return false;
      const aria=el.getAttribute('aria-label');
      const text=(el.textContent||'').trim();
      const id=el.id; const label=id ? document.querySelector(`label[for="${CSS.escape(id)}"]`) : null;
      const parentLabel=el.closest('label'); const placeholder=el.getAttribute('placeholder');
      return !aria && !text && !label && !parentLabel && !placeholder;
    }).map(el=>el.outerHTML)''')
    assert not unnamed, f'unnamed controls: {unnamed}'

def assert_no_horizontal_overflow(page):
    dims=page.evaluate('() => ({sw:document.documentElement.scrollWidth, iw:window.innerWidth})')
    assert dims['sw'] <= dims['iw'] + 2, dims

with sync_playwright() as pw:
    chromium_executable = resolve_chromium_executable()
    launch_options = {
        'headless': True,
        'args': ['--no-sandbox'],
    }
    if chromium_executable is not None:
        launch_options['executable_path'] = chromium_executable

    browser=pw.chromium.launch(**launch_options)

    # Desktop functional flow
    page=browser.new_page(viewport={"width":1440,"height":1050}, device_scale_factor=1)
    errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content(html,wait_until='load'); login(page)
    # RAM-only IPC authentication regression
    assert page.evaluate("sessionStorage.getItem('asf.control.ipcPassword')") is None
    legacy=browser.new_page(viewport={"width":1000,"height":800})
    legacy.set_content(html_legacy_auth,wait_until='load')
    legacy.wait_for_selector('#authGate:not(.hidden)')
    assert legacy.locator('#app').is_hidden()
    assert legacy.evaluate("sessionStorage.getItem('asf.control.ipcPassword')") is None
    assert legacy.evaluate("sessionStorage.getItem('asf.control.view')") == 'dashboard'
    assert legacy.evaluate("sessionStorage.getItem('asf.control.lockMinutes')") == '30'
    login(legacy)
    assert legacy.evaluate("sessionStorage.getItem('asf.control.ipcPassword')") is None
    legacy.close()
    assert page.locator('text=Control Suite 1.1 candidate').count() == 1
    assert_no_horizontal_overflow(page); assert_accessible_controls(page)
    page.screenshot(path=str(SHOT/'dashboard-desktop.png'),full_page=True)

    page.click('#nav button[data-view="accounts"]'); page.wait_for_selector('#requiredInputForm')
    assert page.locator('.full-account-row').count() >= 1
    assert page.locator('.account-display-name',has_text='Mock Main').count() >= 1
    assert page.locator('.account-bot-id',has_text='main').count() >= 1
    assert page.locator('.steam-avatar').count() >= 1
    assert page.locator('.full-account-row .account-meta').first.bounding_box()['width'] > 300
    # Native OnlineStatus is first-class and writes through the native BotConfig endpoint.
    assert page.locator('#onlineStatus').input_value() == '1'
    assert page.locator('[data-native-focus="bot-config"]').count() == 1
    assert page.locator('[data-native-focus="2fa"]').count() == 1
    page.select_option('#onlineStatus','7'); page.click('#saveOnlineStatus')
    page.wait_for_function("() => !document.querySelector('#saveOnlineStatus')?.disabled")
    assert page.evaluate('window.__m.configs.main.OnlineStatus') == 7
    assert page.locator('#onlineStatus').input_value() == '7'

    # Native ASF workspace replaces common legacy administration surfaces.
    page.click('#nav button[data-view="native"]'); page.wait_for_selector('#nativeBotConfig')
    assert page.locator('#nativeGlobalConfig').count() == 1
    assert page.locator('#nativeCommandForm').count() == 1
    assert page.locator('#nativeBgrKeys').count() == 1
    assert page.locator('#nativeAddLicenseApps').count() == 1
    assert page.locator('#nativeRemoveLicenseApps').count() == 1
    assert page.locator('#nativeRedeemKeys').count() == 1
    assert page.locator('#nativeInventoryInfo').count() == 1
    assert page.locator('#nativeInventoryAppId').count() == 1
    assert page.locator('#nativeInventoryContextId').count() == 1
    assert page.locator('#nativeInventoryItems').count() == 1
    assert page.locator('#nativeRedeemPointsDefinition').count() == 1
    assert page.locator('#fetchNative2faToken').count() == 1
    assert page.locator('[data-unban-ip="203.0.113.5"]').count() == 1
    assert page.locator('text=PlaytimeGoals').count() >= 1
    assert page.locator('#nativeLogTail').input_value() == 'mock log line 1\nmock log line 2'

    bot_editor=page.locator('#nativeBotConfig').input_value()
    assert 'SECRET-TOKEN' not in bot_editor
    assert 'SteamTradeToken' not in bot_editor
    assert page.evaluate('window.__m.bgrReads') == 0
    bot_cfg=json.loads(bot_editor)
    bot_cfg['OnlineFlags']=1
    bot_cfg['GamesPlayedWhileIdle']=[123]
    bot_cfg['CustomGamePlayedWhileIdle']='must-be-cleared'
    page.fill('#nativeBotConfig',json.dumps(bot_cfg))
    page.click('#saveNativeBotConfig')
    page.wait_for_function("() => window.__m.configs.main.OnlineFlags === 1")
    assert page.evaluate('window.__m.configs.main.OnlineFlags') == 1
    assert page.evaluate('window.__m.configs.main.SteamTradeToken') == 'SECRET-TOKEN'
    assert page.evaluate('window.__m.configs.main.GamesPlayedWhileIdle') == []
    assert page.evaluate('window.__m.configs.main.CustomGamePlayedWhileIdle') is None

    global_editor=page.locator('#nativeGlobalConfig').input_value()
    assert 'GLOBAL-SECRET' not in global_editor
    assert 'PROXY-SECRET' not in global_editor
    assert 'IPCPassword' not in global_editor
    assert 'LicenseID' not in global_editor
    assert 'WebProxyPassword' not in global_editor
    global_cfg=json.loads(global_editor)
    global_cfg['FarmingDelay']=17
    page.fill('#nativeGlobalConfig',json.dumps(global_cfg))
    page.click('#saveNativeGlobalConfig'); page.wait_for_timeout(320)
    assert page.evaluate('window.__m.globalConfig.FarmingDelay') == 17
    assert page.evaluate('window.__m.globalConfig.IPCPassword') == 'GLOBAL-SECRET'
    assert page.evaluate('window.__m.globalConfig.LicenseID') == '11111111-2222-3333-4444-555555555555'
    assert page.evaluate('window.__m.globalConfig.WebProxyPassword') == 'PROXY-SECRET'

    page.fill('#nativeCommand','status'); page.click('#nativeCommandForm button[type="submit"]'); page.wait_for_timeout(120)
    native_command_output=page.locator('#nativeCommandOutput').input_value()
    if native_command_output != 'OK status':
        print('NATIVE COMMAND DIAGNOSTIC', native_command_output, page.evaluate('window.__m.commands'))
    assert native_command_output == 'OK status'
    assert page.evaluate('window.__m.commands.at(-1)') == 'status'

    # CardsFarmer being idle must not hide live PlaytimeGoals game idling.
    page.evaluate("""() => { window.__m.ptgSnapshot = {
      Bot:'main', Enabled:true, Connected:true, Farming:false, FarmerPaused:false,
      PlayingPossible:true, RecoveryReady:true, CurrentBatch:[10],
      Games:[{AppId:10, Name:'Owned Game', State:'idling'}]
    }; }""")
    page.click('#refreshNativeActivity')
    page.wait_for_function("() => document.querySelector('#nativePlaytimeState')?.dataset.state === 'active'")
    assert page.locator('#nativeCardFarming').get_attribute('data-state') == 'inactive'
    assert page.locator('#nativeOverallActivity').get_attribute('data-state') == 'active'
    assert 'Owned Game' in page.locator('#nativeActiveGames').inner_text()
    page.fill('#nativeCommand','status')
    page.click('#nativeCommandForm button[type="submit"]')
    page.wait_for_timeout(120)
    assert page.locator('#nativeCommandOutput').input_value() == 'OK status'

    # Both inactive: no overall activity.
    page.evaluate("""() => { window.__m.ptgSnapshot = {
      Bot:'main', Enabled:true, Connected:true, Farming:false, FarmerPaused:false,
      PlayingPossible:true, RecoveryReady:true, CurrentBatch:[],
      Games:[{AppId:10, Name:'Owned Game', State:'queued'}]
    }; }""")
    page.click('#refreshNativeActivity')
    page.wait_for_function("() => document.querySelector('#nativePlaytimeState')?.dataset.state === 'queued'")
    assert page.locator('#nativeOverallActivity').get_attribute('data-state') == 'inactive'

    # Missing plugin endpoint is unknown, not inactive.
    page.evaluate("window.__m.ptgUnavailable = true")
    page.click('#refreshNativeActivity')
    page.wait_for_function("() => document.querySelector('#nativePlaytimeState')?.dataset.state === 'unknown'")
    assert page.locator('#nativeOverallActivity').get_attribute('data-state') == 'unknown'
    page.evaluate("window.__m.ptgUnavailable = false; window.__m.ptgSnapshot = null")

    command_count=page.evaluate('window.__m.commands.length')
    page.fill('#nativeCommand','UPDATEPLUGINS'); page.click('#nativeCommandForm button[type="submit"]'); page.wait_for_timeout(120)
    assert 'UPDATEPLUGINS is disabled' in page.locator('#nativeCommandOutput').input_value()
    assert page.evaluate('window.__m.commands.length') == command_count
    page.fill('#nativeCommand','!UPDATEPLUGINS'); page.click('#nativeCommandForm button[type="submit"]'); page.wait_for_timeout(120)
    assert 'UPDATEPLUGINS is disabled' in page.locator('#nativeCommandOutput').input_value()
    assert page.evaluate('window.__m.commands.length') == command_count

    page.fill('#nativeBgrKeys','AAAAA-BBBBB-CCCCC | Test key'); page.click('#queueNativeBgr'); page.wait_for_timeout(320)
    assert page.evaluate('window.__m.bgr.main.UnusedKeys["AAAAA-BBBBB-CCCCC"]') == 'Test key'

    page.fill('#nativeAddLicenseApps','10, 20')
    page.fill('#nativeAddLicensePackages','123')
    page.click('#addNativeLicenses'); page.wait_for_timeout(160)
    assert page.evaluate('window.__m.licenseOps.at(-1)') == ['add','main',{'Apps':[10,20],'Packages':[123]}]

    page.fill('#nativeRemoveLicenseApps','10')
    page.fill('#nativeRemoveLicensePackages','456')
    page.click('#removeNativeLicenses'); page.wait_for_selector('#modal[open]')
    page.fill('#modalConfirmText','REMOVE LICENSES'); page.click('#modalConfirm'); page.wait_for_timeout(180)
    assert page.evaluate('window.__m.licenseOps.at(-1)') == ['remove','main',{'Apps':[10],'Packages':[456]}]

    page.fill('#nativeRedeemKeys','AAAAA-BBBBB-CCCCC\nDDDDD-EEEEE-FFFFF')
    page.click('#redeemNativeKeys'); page.wait_for_timeout(180)
    assert page.evaluate('window.__m.redeemOps.at(-1)') == ['main',{'KeysToRedeem':['AAAAA-BBBBB-CCCCC','DDDDD-EEEEE-FFFFF']}]
    assert 'Results' in page.locator('#nativeRedeemOutput').input_value()

    page.click('#loadNativeInventoryInfo'); page.wait_for_timeout(160)
    assert page.evaluate('window.__m.inventoryReads') == 1
    assert '730' in page.locator('#nativeInventoryInfo').input_value()
    page.fill('#nativeInventoryAppId','730')
    page.fill('#nativeInventoryContextId','2')
    page.fill('#nativeInventoryLanguage','english')
    page.click('#loadNativeInventoryItems'); page.wait_for_timeout(160)
    assert page.evaluate('window.__m.inventoryReads') == 2
    inventory_items=page.locator('#nativeInventoryItems').input_value()
    assert '"AppID": 730' in inventory_items and '"ContextID": 2' in inventory_items and '"Language": "english"' in inventory_items

    page.fill('#nativeRedeemPointsDefinition','42')
    page.click('#redeemNativePoints'); page.wait_for_selector('#modal[open]')
    page.fill('#modalConfirmText','REDEEM POINTS'); page.click('#modalConfirm'); page.wait_for_timeout(180)
    assert page.evaluate('window.__m.pointsOps.at(-1)') == ['main',42,False]

    page.click('#fetchNative2faToken'); page.wait_for_timeout(120)
    assert page.locator('#native2faToken').input_value() == '12345'
    page.click('#loadNative2faConfirmations'); page.wait_for_timeout(120)
    assert 'creator 42' in page.locator('#native2faConfirmations').inner_text()
    page.fill('#nativeAuthenticatorJson','{"shared_secret":"mock"}'); page.click('#importNativeAuthenticator'); page.wait_for_timeout(120)
    assert page.evaluate('window.__m.authenticatorOps.at(-1)[0]') == 'import'

    page.click('[data-unban-ip="203.0.113.5"]'); page.wait_for_timeout(220)
    assert page.evaluate('window.__m.bans.length') == 0

    page.fill('#nativeMassPatch','{"OnlineStatus":7,"TradingPreferences":3}')
    page.check('[data-mass-bot][value="main"]'); page.click('#applyNativeMassPatch'); page.wait_for_timeout(420)
    assert page.evaluate('window.__m.configs.main.TradingPreferences') == 3
    assert page.evaluate('window.__m.configs.main.SteamTradeToken') == 'SECRET-TOKEN'
    assert page.evaluate('window.__m.configs.main.GamesPlayedWhileIdle') == []

    page.fill('#nativeCryptoInput','hello'); page.click('#runNativeHash'); page.wait_for_timeout(120)
    assert page.locator('#nativeCryptoOutput').input_value() == 'HASHED-VALUE'

    assert_accessible_controls(page)
    assert_no_horizontal_overflow(page)

    page.click('#nav button[data-view="accounts"]'); page.wait_for_selector('#requiredInputForm')
    page.fill('#requiredInputValue','12345'); page.click('#requiredInputForm button[type="submit"]'); page.wait_for_timeout(380)
    assert page.evaluate('window.__m.inputs.at(-1)')==['main',{'Type':1,'Value':'12345'}]
    assert page.locator('.toast-title',has_text='Input sent').count() >= 1

    # Password onboarding: plaintext must never reach BotConfig.
    page.click('#createModePassword'); page.fill('input[name="botName"]','newbot'); page.fill('input[name="steamLogin"]','login'); page.fill('input[name="steamPassword"]','PLAINTEXT')
    page.click('#createBotForm button[type="submit"]'); page.wait_for_timeout(480)
    created=page.evaluate('window.__m.configs.newbot')
    assert created['SteamPassword']=='AES-CIPHERTEXT' and created['PasswordFormat']==1 and 'PLAINTEXT' not in json.dumps(created)

    # QR onboarding stays inside Add account, rotates in place without a full Accounts rerender,
    # and automatically restarts after a failed Steam QR session/reconnect.
    page.click('#createModeQr')
    page.wait_for_selector('#addAccountCard #qrOnboardingPanel')
    assert 'QR will appear here after account creation.' in page.locator('#qrOnboardingPanel').inner_text()
    page.fill('input[name="botName"]','qrbot')
    page.click('#createBotForm button[type="submit"]')
    page.wait_for_timeout(900)
    qr_cfg=page.evaluate('window.__m.configs.qrbot')
    assert 'SteamLogin' not in qr_cfg and 'SteamPassword' not in qr_cfg
    assert page.evaluate('window.__m.inputs.some(x=>x[0]==="qrbot"&&x[1].Type===8&&x[1].Value==="Y")')
    page.wait_for_selector('#addAccountCard #qrCode canvas, #addAccountCard #qrCode img, #addAccountCard #qrCode table, #addAccountCard #qrCode svg')
    assert page.locator('#addAccountCard .qr-panel').count()==1
    assert page.locator('.account-workspace #qrCode').count()==0

    page.evaluate('window.__qrAddCardIdentity=document.querySelector("#addAccountCard")')
    page.evaluate('window.__m.accounts.find(a=>a.BotName==="qrbot").QrChallengeUrl="https://s.team/q/TEST-TWO"')
    page.wait_for_timeout(1500)
    assert page.evaluate('window.__qrAddCardIdentity===document.querySelector("#addAccountCard")')
    assert page.locator('#addAccountCard #qrCode').get_attribute('data-qr-url') == 'https://s.team/q/TEST-TWO'

    qr_inputs_before=page.evaluate('window.__m.inputs.filter(x=>x[0]==="qrbot"&&x[1].Type===8&&x[1].Value==="Y").length')
    page.evaluate('''() => {
      const a=window.__m.accounts.find(a=>a.BotName==="qrbot");
      a.QrChallengeUrl=null;
      a.RequiredInput=0;
      a.Connected=false;
    }''')
    page.wait_for_timeout(1400)
    assert 'Reconnecting to Steam' in page.locator('#qrOnboardingStatus').inner_text()
    assert page.evaluate('window.__qrAddCardIdentity===document.querySelector("#addAccountCard")')

    page.evaluate('window.__m.accounts.find(a=>a.BotName==="qrbot").RequiredInput=8')
    page.wait_for_timeout(2700)
    qr_inputs_after=page.evaluate('window.__m.inputs.filter(x=>x[0]==="qrbot"&&x[1].Type===8&&x[1].Value==="Y").length')
    assert qr_inputs_after == qr_inputs_before + 1
    page.wait_for_selector('#addAccountCard #qrCode[data-qr-url="https://s.team/q/TEST-RETRY"]')
    assert page.evaluate('window.__qrAddCardIdentity===document.querySelector("#addAccountCard")')

    # A terminal non-QR input/stopped bot must exit reconnect mode and stop polling.
    page.evaluate('''() => {
      const a=window.__m.accounts.find(a=>a.BotName==="qrbot");
      a.QrChallengeUrl=null;
      a.RequiredInput=1;
      a.KeepRunning=false;
      a.Connected=false;
    }''')
    page.wait_for_timeout(1500)
    assert 'QR login could not continue' in page.locator('#qrOnboardingStatus').inner_text()
    terminal_reads=page.evaluate('window.__m.accountReads')
    page.wait_for_timeout(1800)
    assert page.evaluate('window.__m.accountReads') == terminal_reads
    assert page.evaluate('window.__qrAddCardIdentity===document.querySelector("#addAccountCard")')

    # Restore mock runtime for the remaining account action tests.
    page.evaluate('''() => {
      const a=window.__m.accounts.find(a=>a.BotName==="qrbot");
      a.RequiredInput=0;
      a.KeepRunning=true;
      a.Connected=true;
    }''')

    # Multi-account switcher keeps human identity separate from BotName and scopes actions by BotName.
    page.locator('[data-switch-bot="main"]').click(); page.wait_for_timeout(120)
    assert page.locator('.account-workspace .account-display-name',has_text='Mock Main').count()==1
    page.locator('[data-switch-bot="qrbot"]').click(); page.wait_for_timeout(120)
    page.locator('.account-workspace [data-act="stop"][data-bot="qrbot"]').click(); page.wait_for_timeout(260)
    assert page.evaluate('window.__m.actions.at(-1)')==['qrbot','Stop']
    assert page.evaluate('window.__m.accounts.find(a=>a.BotName==="main").KeepRunning') is True

    # Rename uses the product modal, not browser prompt
    page.locator('[data-act="rename"][data-bot="newbot"]').click(); page.wait_for_selector('#modal[open]')
    page.fill('[data-modal-field="name"]','renamed'); page.click('#modalConfirm'); page.wait_for_timeout(300)
    assert page.evaluate('window.__m.accounts.some(a=>a.BotName==="renamed")')

    # Destructive delete requires exact typed confirmation.
    page.locator('[data-act="delete"][data-bot="renamed"]').click(); page.wait_for_selector('#modal[open]')
    page.fill('#modalConfirmText','wrong'); page.click('#modalConfirm'); page.wait_for_timeout(80)
    assert page.locator('#modal[open]').count()==1 and page.locator('#modalError').inner_text().strip()
    assert page.evaluate('window.__m.accounts.some(a=>a.BotName==="renamed")')
    page.fill('#modalConfirmText','renamed'); page.click('#modalConfirm'); page.wait_for_timeout(320)
    assert not page.evaluate('window.__m.accounts.some(a=>a.BotName==="renamed")')

    # Playtime editor semantics
    page.click('#nav button[data-view="playtime"]'); page.wait_for_selector('#botSelect'); page.select_option('#botSelect','main'); page.wait_for_selector('[data-goal-select][data-appid="10"]')
    assert 'Mock Main' in page.locator('#botSelect option:checked').inner_text()
    sort_reads=page.evaluate('window.__m.libraryReads')
    page.select_option('#goalSort','name-asc'); page.wait_for_timeout(80)
    names=page.locator('[data-goal-row] .goal-select strong').all_inner_texts()
    assert names.index('8AM') < names.index('12 is Better Than 6')
    page.select_option('#goalSort','hours-desc'); page.wait_for_timeout(80)
    assert page.locator('[data-goal-row] .goal-select strong').first.inner_text()=='Owned Game'
    assert page.evaluate('window.__m.libraryReads')==sort_reads
    assert page.locator('[data-goal-select][data-appid="40"]').is_disabled()
    assert not page.locator('[data-goal-select][data-appid="30"]').is_disabled()
    page.uncheck('[data-goal-select][data-appid="30"]'); page.check('[data-goal-select][data-appid="20"]')
    page.fill('[data-goal-target][data-appid="20"]',''); page.fill('#ptgBatch','3'); page.check('#ptgParental')
    page.click('#saveGoals'); page.wait_for_timeout(1000)
    cfg=page.evaluate('window.__m.configs.main')
    assert cfg['PlaytimeGoals']=={'10':2,'20':None}; assert cfg['PlaytimeGoalsBatchSize']==3; assert cfg['PlaytimeGoalsParentalWritesEnabled'] is True
    assert cfg['GamesPlayedWhileIdle']==[] and cfg['CustomGamePlayedWhileIdle'] is None and cfg['OtherPluginSetting']=={'KeepMe':True}
    assert page.locator('pre').count()==0
    assert page.locator('text=Managed status').count()>=1 and page.locator('text=Family View').count()>=1
    assert page.locator('[data-goal-target][data-appid="10"]').get_attribute('step') == 'any'
    assert page.locator('text=1h 0m 0s').count() >= 1
    page.screenshot(path=str(SHOT/'playtime-desktop.png'),full_page=True)

    # System action uses typed native modal confirmation
    page.click('#nav button[data-view="system"]'); page.wait_for_selector('#restartAsf'); page.click('#restartAsf'); page.wait_for_selector('#modal[open]')
    page.fill('#modalConfirmText','RESTART'); page.click('#modalConfirm'); page.wait_for_timeout(180)
    assert page.evaluate('window.__m.restart')==1

    # System remains usable when storage telemetry is unavailable.
    page.evaluate("window.__storageBackup=window.fetch; const orig=window.fetch; window.fetch=async(path,opt={})=>{ if(String(path)==='/Api/ControlCenter/Status'){ const r=await orig(path,opt); const p=await r.json(); p.Result.StorageAvailable=false; p.Result.DiskFreeBytes=null; p.Result.DiskTotalBytes=null; return {ok:true,status:200,statusText:'OK',json:async()=>p}; } return orig(path,opt); };")
    page.click('#refreshView'); page.wait_for_timeout(180)
    assert page.locator('text=unavailable').count() >= 1

    # Native BotConfig copy must be credential-free and must not leak SteamTradeToken.
    # Run this after the dedicated QR flow because a copied credential-free bot correctly
    # enters ASF's QR-required state and should not contaminate the earlier onboarding fixture.
    page.click('#nav button[data-view="native"]'); page.wait_for_selector('#nativeCopyBotName')
    page.fill('#nativeCopyBotName','copy-no-secrets')
    page.click('#copyNativeBotConfig')
    page.wait_for_function("() => Boolean(window.__m.configs['copy-no-secrets'])")
    assert 'SteamTradeToken' not in page.evaluate("window.__m.configs['copy-no-secrets']")
    assert page.evaluate("window.__m.configs['copy-no-secrets'].Enabled") is False
    assert page.evaluate("window.__m.configs['copy-no-secrets'].GamesPlayedWhileIdle") == []

    # Lock clears browser session
    page.click('#nav button[data-view="security"]'); page.click('#lockNow'); page.wait_for_selector('#authGate:not(.hidden)')
    assert page.evaluate("sessionStorage.getItem('asf.control.ipcPassword')") is None
    assert not errors,errors
    page.close()

    # Mobile visual/interaction smoke
    mobile=browser.new_page(viewport={"width":390,"height":844}, device_scale_factor=1)
    mobile_errors=[]; mobile.on('pageerror',lambda e:mobile_errors.append(str(e)))
    mobile.set_content(html,wait_until='load'); login(mobile)
    mobile.click('#nav button[data-view="playtime"]'); mobile.wait_for_selector('#goalRows')
    assert_no_horizontal_overflow(mobile); assert_accessible_controls(mobile)
    assert mobile.locator('.sidebar').evaluate('(e)=>getComputedStyle(e).position')=='fixed'
    mobile.screenshot(path=str(SHOT/'playtime-mobile.png'),full_page=False)
    mobile.click('#nav button[data-view="accounts"]'); mobile.wait_for_selector('#createBotForm')
    assert_no_horizontal_overflow(mobile)
    assert not mobile_errors,mobile_errors
    mobile.close()

    # Locale bridge: ControlWeb must use the exact ASF-ui locale storage key and render uk-UA end-to-end.
    ua=browser.new_page(viewport={"width":1280,"height":900}, device_scale_factor=1)
    ua_errors=[]; ua.on('pageerror',lambda e:ua_errors.append(str(e)))
    ua.set_content(html_uk,wait_until='load')
    ua.wait_for_timeout(100)
    # Auto-detect exactly the locale selected by the stock ASF-ui.
    assert ua.evaluate("localStorage.getItem('asf-ui:locale')") == '"uk-UA"'
    assert ua.locator('#authTitle').inner_text() == 'Підключення до ASF'
    assert ua.locator('#authLocaleSelect').input_value() == 'uk-UA'
    login(ua)
    assert ua.locator('#nav button[data-view="dashboard"] span').nth(1).inner_text() == 'Огляд'
    assert ua.locator('#title').inner_text() == 'Огляд'
    ua.click('#nav button[data-view="accounts"]'); ua.wait_for_selector('#createBotForm'); ua.wait_for_timeout(80)
    assert ua.locator('h3',has_text='Зареєстровані облікові записи').count() == 1
    assert ua.locator('button',has_text='Створити обліковий запис').count() == 1
    assert ua.locator('#qrOnboardingPanel',has_text='QR-код з’явиться тут після створення облікового запису.').count() == 1
    ua.click('#nav button[data-view="playtime"]'); ua.wait_for_selector('#goalRows'); ua.wait_for_timeout(80)
    assert ua.locator('h3',has_text='Налаштування').count() == 1
    assert ua.locator('button',has_text='Зберегти цілі').count() == 1
    assert ua.locator('text=ВЛАСНА').count() >= 1
    ua.click('#nav button[data-view="native"]'); ua.wait_for_selector('#nativeBotConfig'); ua.wait_for_timeout(80)
    assert ua.locator('h3',has_text='Конфігурація бота').count() == 1
    assert ua.locator('h3',has_text='Глобальна конфігурація ASF').count() == 1
    assert ua.locator('h3',has_text='Масовий редактор').count() == 1
    assert ua.locator('h3',has_text='Криптографічні інструменти').count() == 1
    assert ua.locator('h3',has_text='Ліцензії Steam').count() == 1
    assert ua.locator('h3',has_text='Пряма активація ключів').count() == 1
    assert ua.locator('h3',has_text='Інвентар').count() == 1
    assert ua.locator('h3',has_text='Бали Steam').count() == 1
    native_body=ua.locator('#content').inner_text()
    for phrase in ['Bot configuration','Global ASF configuration','Mass editor','Crypto tools','Background redeemer','Copy bot configuration','Steam licenses','Direct key redeem','Inventory','Steam Points']:
        assert phrase not in native_body, phrase
    ua.click('#nav button[data-view="security"]'); ua.wait_for_timeout(80)
    assert ua.locator('h3',has_text='Межа автентифікації').count() == 1
    ua.click('#nav button[data-view="system"]'); ua.wait_for_timeout(80)
    assert ua.locator('h3',has_text='Дії з процесом ASF').count() == 1
    ua.click('#nav button[data-view="advanced"]'); ua.wait_for_timeout(80)
    assert ua.locator('a[href="/bots?asfui=1"]').count() >= 1
    assert ua.locator('h3',has_text='Зафіксована сумісність').count() == 1
    assert ua.locator('h3',has_text='Межі відповідальності').count() == 1
    assert ua.locator('#localeSelect').input_value() == 'uk-UA'
    body=ua.locator('body').inner_text()
    for phrase in ['Registered accounts','Add account','Authentication boundary','ASF process actions','Pinned compatibility','Ownership boundaries','Native API']:
        assert phrase not in body, phrase
    assert_no_horizontal_overflow(ua); assert_accessible_controls(ua)
    ua.screenshot(path=str(SHOT/'dashboard-uk-desktop.png'),full_page=True)
    assert not ua_errors,ua_errors
    ua.close()

    ua_mobile=browser.new_page(viewport={"width":390,"height":844}, device_scale_factor=1)
    ua_mobile_errors=[]; ua_mobile.on('pageerror',lambda e:ua_mobile_errors.append(str(e)))
    ua_mobile.set_content(html_uk,wait_until='load')
    ua_mobile.wait_for_timeout(80); login(ua_mobile)
    ua_mobile.click('#nav button[data-view="playtime"]'); ua_mobile.wait_for_selector('#goalRows'); ua_mobile.wait_for_timeout(100)
    assert_no_horizontal_overflow(ua_mobile); assert_accessible_controls(ua_mobile)
    ua_mobile.screenshot(path=str(SHOT/'playtime-uk-mobile.png'),full_page=False)
    assert not ua_mobile_errors,ua_mobile_errors
    ua_mobile.close()

    # Stock ASF-ui can persist the short "uk" alias. It must still render as Українська,
    # not as a technical "English fallback" option.
    ua_alias=browser.new_page(viewport={"width":900,"height":700})
    ua_alias.set_content(html_uk_alias,wait_until='load'); ua_alias.wait_for_timeout(80)
    assert ua_alias.locator('#authLocaleSelect').input_value() == 'uk-UA'
    assert ua_alias.locator('#authLocaleSelect option:checked').inner_text() == 'Українська'
    assert 'English fallback' not in ua_alias.locator('#authLocaleSelect').inner_text()
    assert ua_alias.locator('#authTitle').inner_text() == 'Підключення до ASF'
    ua_alias.close()

    # Writing locale from Control UI uses the same persisted key as stock ASF-ui.
    bridge=browser.new_page(viewport={"width":900,"height":700})
    bridge.set_content(html,wait_until='load')
    bridge.select_option('#authLocaleSelect','uk-UA'); bridge.wait_for_timeout(80)
    assert bridge.evaluate("localStorage.getItem('asf-ui:locale')") == '"uk-UA"'
    assert bridge.locator('#authTitle').inner_text() == 'Підключення до ASF'
    bridge.close()

    browser.close()

print('UI INTEGRATION: PASS (desktop + mobile + ASF-ui locale bridge uk-UA)')
