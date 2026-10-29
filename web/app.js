"use strict";
/* Souls of Muse — portal SPA (hash routing, static hosting).
   Two modes: light "Ceremony" (home, convention, welcome, card) and
   dark "Workshop" (leagues, cabinets, studio). No success state is shown
   that a real service has not confirmed. */
const S = window.SoulSignature;
const U = window.PortalUtils;
const $ = (s, r=document) => r.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

/* ---------- local UI preferences only (never an account/member/vote store) ---------- */
let prefs = { role:"listener", league:"guitar" };
try { Object.assign(prefs, JSON.parse(localStorage.getItem("som_ui_prefs")||"{}")); } catch(e){}
const savePrefs = () => { try{ localStorage.setItem("som_ui_prefs", JSON.stringify(prefs)); }catch(e){} };

/* ---------- ceremony preview kept in memory between Convention and Welcome ----------
   Not persisted, not an account, no signing date. Falls back to a labelled example. */
const ceremony = { name:"", reading:"", preview:null };
const EXAMPLE = { name:"Haydn" };

/* ---------- canonical seven leagues (emblem slot is neutral: each League chooses its own) ---------- */
const LEAGUES = [
 {id:"guitar", name:"Лига гитары", desc:"Классическая, акустическая и электрогитара: от первых аккордов до концертных программ.", tags:["гитара","ансамбль"]},
 {id:"keys", name:"Лига клавишных", desc:"Фортепиано и клавишные: чтение с листа, ансамбль, импровизация.", tags:["фортепиано","импровизация"]},
 {id:"winds", name:"Лига духовых", desc:"Деревянные и медные духовые: дыхание, строй и ансамблевая игра.", tags:["духовые","ансамбль"]},
 {id:"drums", name:"Лига ударных", desc:"Ритм, перкуссия и ударные установки: пульс живой музыки.", tags:["ритм","перкуссия"]},
 {id:"electronic", name:"Лига электронных", desc:"Синтезаторы, электронное звучание и живое исполнение с технологиями.", tags:["синтезатор","лайв"]},
 {id:"voice", name:"Лига вокала", desc:"Пение, хор и вокальные ансамбли: голос как инструмент.", tags:["вокал","хор"]},
 {id:"folk", name:"Лига народных", desc:"Народные инструменты и традиции живой музыки разных стран.", tags:["традиции","ансамбль"]},
];
const DATA = {
 topics:[
  {id:"t-haydn", t:"Разбираем тему H-A-Y-D-N 1909 года", a:"Пример · ведущий встречи", b:"Как имя Гайдна стало мелодией си–ля–ре–ре–соль и почему буква H звучит как си."},
  {id:"t-tempo", t:"Практика медленного темпа: метроном и дыхание", a:"Пример · участник", b:"Делимся приёмами совместной практики и спокойного темпа."},
  {id:"t-repertoire", t:"Выбираем репертуар к открытому вечеру", a:"Пример · участник", b:"Предложения обсуждаем здесь; решение примет голосование Лиги, когда оно откроется."}],
 events:[
  {id:"e-evening", t:"Открытый вечер живой музыки", w:"Суббота, 19:00 · пример даты", b:"Тёплый вечер Лиги: играем и слушаем вместе. Запись на событие откроется позже."},
  {id:"e-practice", t:"Совместная практика: встреча и упражнения", w:"По расписанию Лиги · пример", b:"Встречаемся, выбираем темп и упражнение, играем по очереди и вместе."}],
 media:[
  {id:"m-rehearsal", t:"Запись открытой репетиции", k:"Аудио · пример записи", b:"Пример карточки медиатеки Лиги. Свои записи можно подготовить в Студии."},
  {id:"m-haydn", t:"Разбор: тема Гайдна за фортепиано", k:"Видео · пример записи", b:"Пример карточки медиатеки Лиги."}],
 members:[
  {id:"u-anna", n:"Пример: Анна", r:"участница"},
  {id:"u-timur", n:"Пример: Тимур", r:"участник"},
  {id:"u-miya", n:"Пример: Мия", r:"участница"}],
 votes:[
  {id:"v-repertoire", t:"Репертуар открытого вечера", st:"Первое голосование ещё не открыто", b:"Ваша подпись — ваш голос в жизни Лиги. Когда голосование откроется, здесь можно будет принять участие."},
  {id:"v-date", t:"Дата следующего вечера", st:"Первое голосование ещё не открыто", b:"Одна подпись — один голос, в любой роли."}],
};
const byId = (tab,id) => (DATA[tab]||[]).find(x=>x.id===id);

/* ---------- score SVG (render of the shared signature module; never redrawn by hand) ---------- */
function scoreSVG(notes){
  if(!notes || !notes.length) return `<p class="score-empty">Здесь появятся ноты вашего имени.</p>`;
  const L = S.layoutScore(notes); let s="", idx=0;
  L.rows.forEach(r=>{
    for(let i=0;i<5;i++) s+=`<line x1="4" x2="${r.end}" y1="${r.top+i*10}" y2="${r.top+i*10}" stroke="#2a2738" opacity=".7"/>`;
    s+=`<text x="8" y="${r.top+30}" font-size="40" fill="#2a2738">\u{1D11E}</text>`;
    r.items.forEach(it=>{ const n=it.n; let g=`<g data-i="${idx++}">`;
      if(it.p<=-2) g+=`<line x1="${it.x-10}" x2="${it.x+10}" y1="${r.top+50}" y2="${r.top+50}" stroke="#16141f"/>`;
      if(it.p>=10) g+=`<line x1="${it.x-10}" x2="${it.x+10}" y1="${r.top-10}" y2="${r.top-10}" stroke="#16141f"/>`;
      g+= it.stemUp?`<line x1="${it.x+5.6}" x2="${it.x+5.6}" y1="${it.y-1}" y2="${it.y-34}" stroke="#16141f"/>`:`<line x1="${it.x-5.6}" x2="${it.x-5.6}" y1="${it.y+1}" y2="${it.y+34}" stroke="#16141f"/>`;
      g+=`<ellipse cx="${it.x}" cy="${it.y}" rx="6" ry="4.2" transform="rotate(-20 ${it.x} ${it.y})" fill="${n.dur===2?"#fff":"#16141f"}" stroke="#16141f"/>`;
      g+=`<text x="${it.x}" y="${r.top+72}" text-anchor="middle" font-size="11" fill="#8f6610">${esc(n.ch)}</text><text x="${it.x}" y="${r.top+84}" text-anchor="middle" font-size="8" fill="#5d5a6e">${S.RU[n.note]}</text></g>`; s+=g; });
    if(r.last) s+=`<line x1="${r.end-1.5}" x2="${r.end-1.5}" y1="${r.top}" y2="${r.top+40}" stroke="#2a2738" stroke-width="3"/>`;
  });
  return `<svg viewBox="0 0 ${L.width} ${L.height}" role="img" aria-label="Нотная подпись">${s}</svg>`;
}

/* ---------- audio playback (only on user gesture) with page cleanup ---------- */
let actx=null, playTimers=[];
function stopPlay(){
  playTimers.forEach(clearTimeout); playTimers=[];
  if(actx){ try{actx.close()}catch(e){} actx=null; }
  const b=$("#playBtn"); if(b) b.textContent="▶ Послушать своё имя";
}
function playNotes(notes){
  if(actx){ stopPlay(); return; }
  const AC=window.AudioContext||window.webkitAudioContext; if(!AC||!notes.length) return;
  actx=new AC(); const beat=60/92, t0=actx.currentTime+.08;
  const master=actx.createGain(); master.gain.value=.3; master.connect(actx.destination);
  let t=0; const b=$("#playBtn"); if(b) b.textContent="⏹ Остановить";
  notes.forEach(n=>{ const f=440*Math.pow(2,(n.midi-69)/12), st=t0+t;
    [[1,"triangle",1],[2,"sine",.25]].forEach(([m,ty,a])=>{ const o=actx.createOscillator(),g=actx.createGain(); o.type=ty;o.frequency.value=f*m;
      g.gain.setValueAtTime(.0001,st); g.gain.exponentialRampToValueAtTime(a,st+.01); g.gain.exponentialRampToValueAtTime(.0001,st+Math.max(.7,n.dur*beat*1.7));
      o.connect(g).connect(master); o.start(st); o.stop(st+Math.max(.75,n.dur*beat*1.8)); }); t+=n.dur*beat; });
  playTimers.push(setTimeout(stopPlay,(t+.9)*1000));
}

/* ---------- member card canvas: fonts+logo ready, long/CJK names fitted inside ---------- */
const logoImg = new Image(); logoImg.src = "assets/logo-a.png";
async function logoReady(){
  if(logoImg.complete && logoImg.naturalWidth) return true;
  try{ if(logoImg.decode) await logoImg.decode(); }catch(e){}
  return logoImg.complete && !!logoImg.naturalWidth;
}
function fitText(ctx, text, fontFor, maxW){
  let size=72;
  while(size>24){ ctx.font=fontFor(size); if(ctx.measureText(text).width<=maxW) return {size, text}; size-=4; }
  ctx.font=fontFor(24);
  let out=text;
  while(out.length>1 && ctx.measureText(out+"…").width>maxW) out=out.slice(0,-1);
  return { size:24, text: out===text?text:out+"…" };
}
function drawCard(canvas, name, notes){
  const ctx=canvas.getContext("2d"), W=1080,H=1350;
  ctx.fillStyle="#0d0b14"; ctx.fillRect(0,0,W,H);
  ctx.strokeStyle="#e9b949"; ctx.lineWidth=2; ctx.strokeRect(40,40,W-80,H-80);
  ctx.textAlign="center";
  if(logoImg.complete && logoImg.naturalWidth){
    const lh=118, lw=lh*logoImg.naturalWidth/logoImg.naturalHeight;
    ctx.drawImage(logoImg, W/2-lw/2, 44, lw, lh);
  } else {
    ctx.fillStyle="#e9b949"; ctx.font='500 22px "JetBrains Mono",monospace';
    ctx.fillText("S O U L S   O F   M U S E", W/2, 132);
  }
  ctx.fillStyle="#f4f1ea"; ctx.font='600 64px "Cormorant Garamond","Noto Serif JP","Noto Serif KR",Georgia,serif';
  ctx.fillText("Конвенция хранителей", W/2, 230); ctx.fillText("живой музыки", W/2, 306);
  ctx.fillStyle="#cdb980"; ctx.font='italic 500 34px "Cormorant Garamond",Georgia,serif';
  ctx.fillText("Convention of the Keepers of Live Music", W/2, 362);
  if(notes.length){ const L=S.layoutScore(notes,{perRow:12,rowH:92}); const sc=Math.min(880/L.width,380/L.height,3.1);
    ctx.save(); ctx.translate((W-L.width*sc)/2, 470+(380-L.height*sc)/2); ctx.scale(sc,sc);
    L.rows.forEach(r=>{ ctx.strokeStyle="#e9b949"; for(let i=0;i<5;i++){ctx.beginPath();ctx.moveTo(4,r.top+i*10);ctx.lineTo(r.end,r.top+i*10);ctx.stroke();}
      ctx.fillStyle="#e9b949"; ctx.font='40px "Noto Music",serif'; ctx.textAlign="left"; ctx.fillText("\u{1D11E}",8,r.top+30);
      r.items.forEach(it=>{ const n=it.n; ctx.strokeStyle="#f4f1ea"; ctx.beginPath();
        if(it.stemUp){ctx.moveTo(it.x+5.6,it.y-1);ctx.lineTo(it.x+5.6,it.y-34);}else{ctx.moveTo(it.x-5.6,it.y+1);ctx.lineTo(it.x-5.6,it.y+34);} ctx.stroke();
        ctx.beginPath(); ctx.ellipse(it.x,it.y,6,4.2,-.35,0,Math.PI*2); if(n.dur===2){ctx.strokeStyle="#f4f1ea";ctx.stroke();}else{ctx.fillStyle="#f4f1ea";ctx.fill();}
        ctx.fillStyle="#e9b949"; ctx.textAlign="center"; ctx.font='11px monospace'; ctx.fillText(n.ch,it.x,r.top+70); }); });
    ctx.restore(); }
  ctx.textAlign="center";
  const cjk=/[\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7a3]/.test(name||"");
  const fitted=fitText(ctx, name||"—", s=>`${cjk?"600":"italic 600"} ${s}px "Cormorant Garamond","Noto Serif JP","Noto Serif KR",Georgia,serif`, 880);
  ctx.fillStyle="#f4f1ea"; ctx.font=`${cjk?"600":"italic 600"} ${fitted.size}px "Cormorant Garamond","Noto Serif JP","Noto Serif KR",Georgia,serif`;
  ctx.fillText(fitted.text, W/2, 1000);
  ctx.fillStyle="#a29eb5"; ctx.font='26px system-ui,sans-serif';
  ctx.fillText("Предпросмотр карточки участника", W/2, 1060);
  ctx.fillStyle="#e9b949"; ctx.font='500 19px monospace';
  ctx.fillText("ХРАНИТЕЛЬ ЖИВОЙ МУЗЫКИ · KEEPER OF LIVE MUSIC", W/2, 1210);
}
async function renderCard(canvas, name, notes){
  if(document.fonts && document.fonts.ready){ try{ await document.fonts.ready; }catch(e){} }
  await logoReady();
  if(!canvas.isConnected) return;
  drawCard(canvas, name, notes);
}
async function downloadCard(name, notes){
  const c=document.createElement("canvas"); c.width=1080; c.height=1350;
  if(document.fonts && document.fonts.ready){ try{ await document.fonts.ready; }catch(e){} }
  await logoReady();
  drawCard(c,name,notes);
  c.toBlob(b=>{ if(!b) return; const a=document.createElement("a"); a.href=URL.createObjectURL(b); a.download="souls-of-muse-card-preview.png"; a.click(); setTimeout(()=>URL.revokeObjectURL(a.href),4000); },"image/png");
}

/* ---------- shared chrome: mode decides Ceremony (light) vs Workshop (dark) ---------- */
const ROLES={student:"Ученик",teacher:"Учитель",listener:"Слушатель"};
function chrome(mode, inner){
  return `<a class="skip" href="#main">К содержанию</a>
  <header class="topbar"><a class="brand" href="#/">Souls of <em>Muse</em></a>
  <nav class="main" aria-label="Основная навигация">
    <a href="#/">Главная</a><a href="#/convention">Конвенция</a><a href="#/welcome">Welcome</a><a href="#/leagues">Лиги</a>
    <a href="#/cabinet/${prefs.role}">Кабинет</a><a href="#/studio">Студия</a><a href="lesson.html">Урок · preview</a></nav>
  <div class="role-switch" role="group" aria-label="Активная роль одной учётной записи"><span>Роль:</span>
    ${Object.entries(ROLES).map(([k,v])=>`<button type="button" data-role="${k}" aria-pressed="${prefs.role===k}">${v}</button>`).join("")}</div></header>
  <main id="main" tabindex="-1">${inner}</main>
  <footer class="site">Souls of Muse — сообщество хранителей живой музыки. Ваша карточка — знак участия и ваша подпись-голос в жизни Лиги. Вопросы: <a href="mailto:muse@soulsofmuse.com">muse@soulsofmuse.com</a></footer>`;
}

/* ---------- views (pure HTML; binding happens after insertion, see binders) ---------- */
function vHome(){ return chrome("ceremony", `
 <p class="eyebrow">Convention of the Keepers of Live Music</p>
 <h1>Ваше имя может <em>звучать</em></h1>
 <p class="lede">Souls of Muse — тёплое сообщество хранителей живой музыки. Здесь ваше имя становится мелодией и личной подписью, а впереди — Лиги по душе, уроки, открытые вечера и совместная практика. Учиться, учить или просто слушать — каждый путь здесь полноценный.</p>
 <p><a class="btn" href="#/convention">Услышать своё имя и присоединиться</a> <a class="btn ghost" href="#/welcome">Посмотреть Welcome</a></p>
 <div class="grid c3">
  <div class="card light"><h3>Конвенция</h3><p>Имя или псевдоним — и вы видите и слышите свою музыкальную подпись.</p><a href="#/convention">Открыть →</a></div>
  <div class="card light"><h3>Welcome и карточка</h3><p>Личная карточка, медаль за участие и ваш голос в жизни сообщества — как подарок за то, что вы пришли.</p><a href="#/welcome">Посмотреть →</a></div>
  <div class="card light"><h3>Семь Лиг</h3><p>Гитара, клавишные, духовые, ударные, электронные, вокал и народные — выберите свою и заходите.</p><a href="#/leagues">Каталог Лиг →</a></div>
 </div>`); }

function vConvention(){
  const name = ceremony.name || "";
  return chrome("ceremony", `
 <p class="eyebrow">Конвенция хранителей живой музыки · Convention of the Keepers of Live Music</p>
 <h1>Ваше имя — <em>ваша подпись</em></h1>
 <div class="grid c2"><section class="paper" aria-labelledby="conv-text"><h2 id="conv-text">Конвенция хранителей живой музыки</h2>
 <p>Я, нижеподписавшийся, отдаю дань уважения такому великому дару человечества, как музыка, и обязуюсь сохранять и развивать умение людей сочинять, исполнять и передавать другим людям музыкальные произведения.</p>
 <p>Множество предыдущих поколений музыкантов последовательно создали великую музыкальную вселенную, в которой мы сейчас живём. Я готов поддерживать эту традицию: делиться с другими участниками Конвенции или с благодарностью принимать от них умение играть на музыкальных инструментах, владение вокалом, знания по теории музыки, практику коллективного исполнения музыки и совместного прослушивания живой музыки.</p>
 <p>Как участник Конвенции, я буду всячески поддерживать авторские права создателей музыкальных произведений и заботиться о сохранении музыкальных знаний.</p>
 <p>Я постараюсь играть живую музыку чаще, чем делаю это сейчас, чтобы подарить опыт прослушивания музыки, создаваемой непосредственно играющим музыкантом, как можно большему количеству окружающих меня людей.</p>
 <p>Принимая участие в деятельности сообщества Конвенции, обязуюсь соблюдать все принятые в нём правила общения между участниками, но оставляю за собой право на свободу художественного самовыражения в выбранном мною направлении музыкального творчества!</p>
 <details lang="en"><summary>Convention of the Keepers of Live Music (English)</summary>
 <p>I, the undersigned, honour music as one of humanity’s greatest gifts by pledging to preserve and develop people’s ability to compose, perform and pass musical works on to others.</p>
 <p>Many generations of musicians before us have built, generation after generation, the great musical universe in which we live today. I am ready to carry this tradition forward by sharing with other participants in this Convention—or gratefully learning from them—instrumental and vocal skills, knowledge of music theory, the practice of making music together, and the shared experience of listening to live music.</p>
 <p>As a participant in this Convention, I will respect and uphold the copyright of those who create musical works, and help preserve musical knowledge.</p>
 <p>I will strive to play live music more often than I do now, so that as many people around me as possible may experience music performed live, directly by a musician.</p>
 <p>In taking part in the Convention’s community, I pledge to follow all its adopted rules for communication between participants, while retaining my right to freedom of artistic expression in the musical direction I choose.</p></details>
 <details><summary>Как имя становится музыкой</summary><p>В 1909 году имя HAYDN записали нотами: H–A–Y–D–N прозвучало как си–ля–ре–ре–соль. С тех пор буквы, слоги каны по поэме «Ироха» и слоги хангыля по родным названиям нот превращаются в мелодию по одним и тем же правилам. Если в имени есть иероглифы, их чтение указываете вы сами — оно только ваше.</p></details>
 </section>
 <section class="paper" aria-labelledby="sign-preview"><h2 id="sign-preview">Ваша подпись <span class="badge soft">preview</span></h2>
 <label>Имя или псевдоним <input id="nm" autocomplete="off" value="${esc(name)}" placeholder="Например, Haydn"></label>
 <label id="readingWrap" hidden>Чтение имени — его указываете вы сами <input id="rd" autocomplete="off" value="${esc(ceremony.reading)}" placeholder="Кана, хангыль или латиница"></label>
 <p id="notesLine" aria-live="polite"></p>
 <div class="score-box" id="scoreBox"></div>
 <p><button class="btn" id="playBtn" type="button">▶ Послушать своё имя</button></p>
 <p><button class="btn" id="joinBtn" type="button">Присоединиться</button> <span id="joinState" role="status"></span></p>
 <p><a href="#/welcome">Посмотреть, как встретит вас Welcome →</a></p>
 </section></div>`);
}

function currentWelcomePerson(){
  if(ceremony.preview && ceremony.name.trim() && ceremony.preview.notes.length){
    return { name:ceremony.name.trim(), reading:ceremony.reading, preview:ceremony.preview, isExample:false };
  }
  return { name:EXAMPLE.name, reading:"", preview:S.previewSignature(EXAMPLE.name,""), isExample:true };
}
function vWelcome(){
  const p = currentWelcomePerson();
  return chrome("ceremony", `
 <p class="eyebrow">Welcome · Souls of Muse</p>
 <h1>Добро пожаловать, <em>${esc(p.name)}</em></h1>
 ${p.isExample
   ? `<p class="demo-banner" role="note">Это пример Welcome на имени Haydn. На странице Конвенции введите своё имя — и здесь зазвучит именно оно.</p>`
   : `<p class="demo-banner" role="note">Предпросмотр: вы видите подпись, которую только что собрали на странице Конвенции. Она ещё не подтверждена как подпись участника.</p>`}
 <img class="brand-logo" src="assets/logo-a.png" alt="Общая эмблема сообщества: золотая лира в венке" width="1374" height="1145">
 <div class="grid c2"><section class="paper"><h2>Ваша музыкальная подпись</h2><div class="score-box">${scoreSVG(p.preview.notes)}</div>
 <p>Ноты: ${esc(p.preview.note_names_ru.join(" – "))}. Каждая буква и каждый слог вашего имени встали на своё место на нотном стане — и теперь это можно услышать.</p>
 <p><button class="btn" id="playBtn" type="button">▶ Послушать своё имя</button></p>
 <details><summary>Откуда взялась подпись</summary><p>Имя раскладывается по нотным сеткам: латиница — по французской сетке 1909 года, кана — по поэме «Ироха», хангыль — по корейским названиям нот. Каждая следующая нота выбирает ближайшую октаву, чтобы мелодия пелась. Одно имя — всегда одна и та же подпись.${p.reading?` Ваше чтение имени: ${esc(p.reading)}.`:""}</p></details>
 <div class="seal-slot" aria-label="Место личной печати"><span>Здесь будет ваша личная печать: нотная подпись вместо имени, вписанная в знак сообщества. Её упрощённый дизайн ещё создаётся — мы не подменим её чужой печатью.</span></div>
 </section>
 <section class="card light"><h2>Ваша карточка</h2><canvas id="cardCanvas" width="1080" height="1350" aria-label="Карточка участника"></canvas>
 <p>Карточка — ваш знак участия: её приятно сохранить и показать. А ещё это ваша подпись-голос: с ней вы участвуете в жизни и управлении своей Лиги. Первое голосование ещё не открыто — мы бережно готовим его вместе с сообществом.</p>
 <p><button class="btn ghost" id="dlCard" type="button">Скачать карточку (PNG)</button></p>
 <div class="medal"><h3>Медаль за участие</h3><p>«Хранитель живой музыки» — за то, что вы пришли и приняли участие. Стиль оформления выбираете вы сами; смысл награды один во всех стилях.</p>
 <figure><img class="honors-img" src="assets/honors-playful.png" alt="Игровая линия наград с Muse в берете: брелок, медаль и рамка аватара" width="1997" height="788"><figcaption>Игровая линия наград — полный набор как просмотр стиля. <span class="badge soft">preview</span></figcaption></figure>
 <details><summary>Классическая линия наград</summary><figure><img class="honors-img" src="assets/honors-formal.png" alt="Классическая парадная линия наград" width="1536" height="1024" loading="lazy"><figcaption>Классическая линия — полный набор как просмотр стиля. <span class="badge soft">preview</span></figcaption></figure></details></div>
 <h3>Одна ясная следующая цель</h3><p>Выберите Лигу и — как ученик, учитель или слушатель — войдите в свой кабинет.</p>
 <p><a class="btn" href="#/leagues">Выбрать Лигу и войти →</a></p></section></div>`);
}

function vLeagues(){
  return chrome("workshop", `<p class="eyebrow">Каталог · Мастерская</p><h1>Семь Лиг сообщества</h1>
  <p class="lede">Эмблему каждая Лига выбирает сама. Мы предлагаем основу — и с уважением примем любой выбор Лиги. Выберите свою:</p>
  <div class="toolbar"><label>Поиск <input id="q" type="search" placeholder="Название или занятие"></label>
  <label>Фильтр <select id="tag"><option value="">Все Лиги</option>${[...new Set(LEAGUES.flatMap(l=>l.tags))].map(t=>`<option>${t}</option>`).join("")}</select></label></div>
  <div class="grid c2" id="leagueGrid"></div>`);
}

function vLeague(id, tab){
  const resolved = U.resolveLeague(id, tab, LEAGUES.map(l=>l.id), prefs.league);
  const l = LEAGUES.find(x=>x.id===resolved.id) || LEAGUES[0];
  if(resolved.idValid){ prefs.league=l.id; savePrefs(); }
  const TABS=[["topics","Обсуждения"],["events","События"],["media","Медиатека"],["members","Участники"],["votes","Голосования"]];
  const initial = resolved.tab;
  return chrome("workshop", `<p class="eyebrow">Пространство Лиги</p><h1>${esc(l.name)}</h1><p class="lede">${esc(l.desc)}</p>
  <div class="emblem-slot">Эмблема Лиги появится здесь — её выберет сама Лига.</div>
  <p><a class="btn ghost" href="#/leagues">← Каталог Лиг</a> <a class="btn ghost" href="#/welcome">Welcome</a> <a class="btn" href="#/cabinet/${prefs.role}">Мой кабинет (${ROLES[prefs.role]})</a></p>
  <div class="tabs" role="tablist" aria-label="Разделы Лиги">${TABS.map(([k,v])=>`<button role="tab" data-tab="${k}" id="tab-${k}" aria-controls="tabBody" aria-selected="${k===initial}" tabindex="${k===initial?"0":"-1"}">${v}</button>`).join("")}</div>
  <div class="toolbar"><label>Поиск по разделу <input id="lq" type="search"></label></div>
  <div id="tabBody" class="list" role="tabpanel" aria-labelledby="tab-${initial}"></div>
  <dialog id="dlg" aria-labelledby="dlgT"><h3 id="dlgT"></h3><p id="dlgB"></p><p id="dlgAct"></p><button class="btn" id="dlgClose" type="button">Закрыть (Esc)</button></dialog>`);
}

function lessonForkHTML(){
  return `<div class="card"><h3>Занятия: выберите форму</h3>
   <p><button class="btn small" data-lesson="individual" type="button">Индивидуальное занятие</button>
   <button class="btn small ghost" data-lesson="group" type="button">Групповое занятие</button></p>
   <p data-lesson-msg role="status">Индивидуальное занятие можно посмотреть в существующем макете урока (preview).</p></div>`;
}
function vCabinet(role){
  prefs.role = role in ROLES ? role : "listener"; savePrefs();
  const l=LEAGUES.find(x=>x.id===prefs.league)||LEAGUES[0];
  const blocks={
   student:{h:"Кабинет ученика", main:"Продолжить учёбу", body:`
     ${lessonForkHTML()}
     <div class="card"><h3>Практика</h3><p>Метроном и упражнения совместной практики — в Студии.</p><a href="#/studio">Студия и метроном →</a></div>
     <div class="card"><h3>Материалы Лиги</h3><p>Медиатека и обсуждения вашей Лиги.</p><a href="#/league/${l.id}/media">Медиатека Лиги →</a> · <a href="#/league/${l.id}/topics">Обсуждения →</a></div>`},
   teacher:{h:"Кабинет учителя", main:"Подготовиться к занятию", body:`
     ${lessonForkHTML()}
     <div class="card"><h3>Ученики и материалы</h3><p>Группы и списки учеников появятся здесь, когда Лига начнёт занятия. Материалы можно подготовить уже сейчас.</p><a href="#/studio">Студия →</a> · <a href="#/league/${l.id}">Моя Лига →</a></div>
     <div class="card"><h3>События Лиги</h3><p>Открытые вечера и совместные практики вашей Лиги.</p><a href="#/league/${l.id}/events">События «${esc(l.name)}» →</a></div>`},
   listener:{h:"Кабинет слушателя", main:"Слушать живую музыку", body:`
     <div class="card"><h3>Вы — часть музыки</h3><p>Музыка живёт, пока её слушают. Слушатель — такая же часть живой музыки, как тот, кто играет.</p></div>
     <div class="card"><h3>События и вечера</h3><p>Открытые вечера и встречи вашей Лиги — приходите слушать.</p><a class="btn" href="#/league/${l.id}/events">События «${esc(l.name)}» →</a></div>
     <div class="card"><h3>Сохранённое и медиатека</h3><p>Записи Лиги и ваши собственные записи из Студии — они остаются на вашем устройстве, пока вы их не скачаете.</p><a href="#/league/${l.id}/media">Медиатека →</a> · <a href="#/studio">Студия →</a></div>`},
  }[prefs.role];
  return chrome("workshop", `
  <p class="eyebrow">${blocks.h} · ${esc(l.name)} · preview</p><h1>${blocks.main}</h1>
  <div class="muse-hint"><img src="assets/muse-original.png" alt="Muse в берете — подсказка сервиса" width="72" height="72"><p><strong>Muse рядом.</strong> Я подскажу, где уроки, события и ваши записи — просто идите за музыкой.</p></div>
  <p><a class="btn ghost" href="#/welcome">← Welcome и карточка</a> <a class="btn ghost" href="#/leagues">Лиги</a></p>
  <div class="grid c3">${blocks.body}</div>`);
}

function vStudio(){
  return chrome("workshop", `<p class="eyebrow">Студия · Мастерская</p><h1>Запись, файлы и совместная практика</h1>
  <p class="lede">Запись начинается только по вашей кнопке и с вашего согласия, и всё время записи виден её знак. Созданное здесь хранится на этом устройстве — скачать файл можно сразу.</p>
  <div class="grid c2">
  <section class="card"><h2>Запись аудио / видео</h2>
   <label>Тип <select id="recKind"><option value="audio">Аудио (микрофон)</option><option value="video">Видео (камера и микрофон)</option></select></label>
   <label class="check"><input type="checkbox" id="recConsent"> Я соглашаюсь включить микрофон/камеру для записи на этом устройстве</label>
   <p><button class="btn" id="recStart" type="button">Начать запись</button> <button class="btn ghost" id="recStop" type="button" disabled>Остановить</button> <span id="recInd" role="status"></span></p>
   <div id="recOut"></div><p id="recMsg" role="status"></p></section>
  <section class="card"><h2>Свой файл</h2>
   <label>Выбрать аудио/видео файл <input id="fileIn" type="file" accept="audio/*,video/*"></label>
   <div id="filePrev"></div>
   <label>Название <input id="metaT"></label><label>Описание <textarea id="metaD" rows="2"></textarea></label>
   <label>Кому будет видно <select id="metaV"><option>Только мне</option><option>Группе</option><option>Лиге</option><option>Всем</option></select></label>
   <label class="check"><input type="checkbox" id="pubConsent"> Когда публикация записей откроется, я соглашаюсь показать эту запись выбранному кругу</label>
   <p><button class="btn ghost" id="saveDraft" type="button">Сохранить черновик на этом устройстве</button> <span id="draftMsg" role="status"></span></p>
   <p>Публикация записей ещё не открыта: файл остаётся у вас.</p></section>
  <section class="card"><h2>Метроном</h2>
   <label>Темп: <span id="bpmVal">92</span> BPM <input id="bpm" type="range" min="40" max="180" value="92"></label>
   <p><button class="btn" id="metroBtn" type="button">Включить метроном</button></p><p>Звук — только после вашего нажатия.</p></section>
  <section class="card"><h2>Встреча для совместной практики</h2>
   <label>Название встречи <input id="sessT" value="Вечерняя практика"></label>
   <label>Упражнение <select id="sessEx"><option>Гаммы в общем темпе</option><option>Игра по очереди, по кругу</option><option>Чтение с листа</option><option>Музыкальная игра: эхо ритма</option></select></label>
   <label>Ведущий и гости <select id="sessR"><option>Ведущий — учитель</option><option>Ведущий — участник</option><option>Можно прийти послушать</option></select></label>
   <p><button class="btn" id="sessBtn" type="button">Составить план встречи</button></p>
   <div id="sessOut" class="list"></div>
   <p>Это план встречи на этом устройстве. Живая совместная игра по сети ещё не открыта.</p></section>
  </div>
  <p><a class="btn ghost" href="#/welcome">← Welcome</a> <a class="btn ghost" href="#/leagues">Лиги</a></p>`);
}

/* ---------- binders (single post-render lifecycle; no dead duplicates) ---------- */
function bindCommon(){
  const skip=document.querySelector(".skip");
  if(skip) skip.addEventListener("click", e=>{ e.preventDefault();
    const m=$("#main"); if(m){ m.focus({preventScroll:false}); m.scrollIntoView(); } });
  /* aria-current on the nav section matching the current hash */
  const h=location.hash||"#/";
  const section = h==="#/"||h==="" ? "#/" : h.startsWith("#/convention") ? "#/convention"
    : h.startsWith("#/welcome") ? "#/welcome"
    : h.startsWith("#/leagues")||h.startsWith("#/league/") ? "#/leagues"
    : h.startsWith("#/cabinet/") ? "#/cabinet/"+prefs.role
    : h.startsWith("#/studio") ? "#/studio" : null;
  document.querySelectorAll("nav.main a").forEach(a=>{
    if(section && a.getAttribute("href")===section) a.setAttribute("aria-current","page");
    else a.removeAttribute("aria-current");
  });
  document.querySelectorAll("[data-role]").forEach(b=>b.onclick=()=>{
    prefs.role=b.dataset.role; savePrefs(); location.hash="#/cabinet/"+prefs.role;
  });
  document.querySelectorAll("[data-lesson]").forEach(b=>b.onclick=()=>{
    const card=b.closest(".card"), msg=card && card.querySelector("[data-lesson-msg]"); if(!msg) return;
    if(b.dataset.lesson==="individual"){ msg.innerHTML=`Индивидуальное занятие: <a href="lesson.html">открыть макет урока (preview)</a>.`; }
    else { msg.textContent="Групповое занятие: его экран ещё готовится — мы не покажем заготовку за готовый урок. Индивидуальное занятие доступно рядом."; }
  });
}
function bindConvention(){
  const upd=()=>{
    ceremony.name=$("#nm").value; ceremony.reading=$("#rd").value;
    ceremony.preview=S.previewSignature(ceremony.name, ceremony.reading);
    const p=ceremony.preview;
    $("#readingWrap").hidden=!p.has_han;
    $("#notesLine").textContent=p.need_reading
      ? "В вашем имени есть иероглифы. Их чтение знаете только вы — впишите его, и подпись соберётся."
      : (p.notes.length ? "Ваши ноты: "+p.note_names_ru.join(" – ") : "Начните вводить имя — и оно зазвучит.");
    $("#scoreBox").innerHTML=scoreSVG(p.notes);
  };
  $("#nm").addEventListener("input",upd); $("#rd").addEventListener("input",upd); upd();
  $("#playBtn").onclick=()=>{ if(ceremony.preview) playNotes(ceremony.preview.notes); };
  $("#joinBtn").onclick=()=>{
    $("#joinState").textContent="Текст Конвенции перед вами. Само присоединение подтвердится отдельным шагом, который ещё готовится, — а ваша подпись уже ждёт вас: загляните, как встретит Welcome.";
  };
}
function bindWelcome(){
  const p=currentWelcomePerson();
  renderCard($("#cardCanvas"), p.name, p.preview.notes);
  $("#playBtn").onclick=()=>playNotes(p.preview.notes);
  $("#dlCard").onclick=()=>downloadCard(p.name, p.preview.notes);
}
function bindLeagues(){
  const draw=()=>{ const q=$("#q").value.toLowerCase(), tg=$("#tag").value;
    const list=LEAGUES.filter(l=>(!tg||l.tags.includes(tg))&&(!q||(l.name+l.desc+l.tags.join(" ")).toLowerCase().includes(q)));
    $("#leagueGrid").innerHTML=list.length?list.map(l=>`<article class="card"><div class="emblem-slot small">Эмблему выберет сама Лига</div><h3>${esc(l.name)}</h3><p>${esc(l.desc)}</p><p>${l.tags.map(t=>`<span class="badge dim">${esc(t)}</span>`).join(" ")}</p><button class="btn" data-enter="${l.id}" type="button">Войти в Лигу</button></article>`).join(""):`<p>Ничего не нашлось. Попробуйте другое слово.</p>`;
    document.querySelectorAll("[data-enter]").forEach(b=>b.onclick=()=>{ prefs.league=b.dataset.enter; savePrefs(); location.hash="#/league/"+prefs.league; }); };
  $("#q").addEventListener("input",draw); $("#tag").addEventListener("change",draw); draw();
}
function bindLeague(initialTab, leagueId){
  const resolved = U.resolveLeague(leagueId, initialTab, LEAGUES.map(l=>l.id), prefs.league);
  let tab = resolved.tab;
  const renderT=()=>{ const q=($("#lq").value||"").toLowerCase();
    const panel=$("#tabBody"); if(panel) panel.setAttribute("aria-labelledby","tab-"+tab);
    document.querySelectorAll("[data-tab]").forEach(x=>{ const on=x.dataset.tab===tab;
      x.setAttribute("aria-selected",String(on)); x.tabIndex = on?0:-1; });
    const filt=a=>a.filter(x=>JSON.stringify(x).toLowerCase().includes(q)); let html="";
    if(tab==="members") html=filt(DATA.members).map(m=>`<div class="item"><strong>${esc(m.n)}</strong><p>${esc(m.r)} · пример участника</p></div>`).join("");
    else if(tab==="votes") html=filt(DATA.votes).map(v=>`<div class="item" data-id="${v.id}"><strong>${esc(v.t)}</strong> <span class="badge">${esc(v.st)}</span><p>${esc(v.b)}</p><button class="btn small" data-vote="${v.id}" type="button">Участвовать</button> <span role="status"></span></div>`).join("");
    else html=filt(DATA[tab]).map(x=>`<button class="item" data-open="${x.id}" type="button"><strong>${esc(x.t)}</strong><p>${esc(x.w||x.k||x.a||"")}</p><p>${esc(x.b)}</p></button>`).join("");
    $("#tabBody").innerHTML=html||`<p>Здесь пока пусто. <a href="#/leagues">Вернуться в каталог</a></p>`;
    document.querySelectorAll("[data-open]").forEach(b=>b.onclick=()=>{
      const x=byId(tab, b.dataset.open); if(!x) return;
      $("#dlgT").textContent=x.t; $("#dlgB").textContent=x.b;
      $("#dlgAct").innerHTML = tab==="events"
        ? `<button class="btn small" id="dlgReg" type="button">Записаться</button> <span role="status" id="dlgRegMsg"></span>`
        : tab==="media" ? `Свои записи готовятся в <a href="#/studio">Студии</a>.` : `Обсуждение откроется вместе с жизнью Лиги.`;
      $("#dlg").showModal();
      const reg=$("#dlgReg"); if(reg) reg.onclick=()=>{ $("#dlgRegMsg").textContent="Запись на событие ещё не открыта."; };
    });
    document.querySelectorAll("[data-vote]").forEach(b=>b.onclick=()=>{
      b.nextElementSibling.textContent="Первое голосование ещё не открыто — ваш голос будет ждать своего дня.";
    }); };
  const tabBtns=[...document.querySelectorAll("[data-tab]")];
  const activate=(btn)=>{ if(!btn) return;
    if(btn.dataset.tab!==tab && leagueId){ focusTabOnRender=true; location.hash=`#/league/${leagueId}/${btn.dataset.tab}`; return; }
    tab=btn.dataset.tab; renderT(); btn.focus(); };
  tabBtns.forEach((b,i)=>{
    b.onclick=()=>activate(b);
    b.addEventListener("keydown", e=>{
      const ni=U.tabIndexForKey(e.key, i, tabBtns.length);
      if(ni!==i){ e.preventDefault(); activate(tabBtns[ni]); if(tabBtns[ni].dataset.tab===tab) tabBtns[ni].focus(); }
    });
  });
  $("#lq").addEventListener("input",renderT);
  $("#dlgClose").onclick=()=>$("#dlg").close();
  renderT();
}

/* ---------- studio: recorder/metronome lifecycle with idempotent cleanup ---------- */
const studio = { mr:null, stream:null, chunks:[], pending:false, generation:0,
                 metroTimer:null, metroCtx:null, objectUrls:[] };
function stopTracks(){
  if(studio.stream){ studio.stream.getTracks().forEach(t=>{ try{t.stop()}catch(e){} }); studio.stream=null; }
}
function cleanupStudio(){
  studio.generation++;                       /* invalidate pending callbacks */
  if(studio.mr){ try{ if(studio.mr.state!=="inactive") studio.mr.stop(); }catch(e){} studio.mr=null; }
  stopTracks();
  if(studio.metroTimer){ clearInterval(studio.metroTimer); studio.metroTimer=null; }
  if(studio.metroCtx){ try{ studio.metroCtx.close(); }catch(e){} studio.metroCtx=null; }
  studio.objectUrls.forEach(u=>{ try{URL.revokeObjectURL(u)}catch(e){} }); studio.objectUrls=[];
  studio.pending=false; studio.chunks=[];
}
function bindStudio(){
  let gen = studio.generation;
  const alive = () => studio.generation===gen && document.getElementById("recStart");
  $("#recStart").onclick=async()=>{ const msg=$("#recMsg");
    if(studio.pending) return;                       /* lock against double click */
    if(!$("#recConsent").checked){ msg.textContent="Сначала отметьте согласие на запись."; return; }
    if(!navigator.mediaDevices || !window.MediaRecorder){ msg.textContent="Запись в этом браузере недоступна. Можно выбрать собственный файл рядом."; return; }
    studio.pending=true; $("#recStart").disabled=true;
    let stream=null;
    try{
      const kind=$("#recKind").value;
      stream = kind==="video"
        ? await navigator.mediaDevices.getUserMedia({audio:true,video:true})
        : await navigator.mediaDevices.getUserMedia({audio:true});
    }catch(e){
      if(stream) stream.getTracks().forEach(t=>t.stop());
      studio.pending=false;
      if(alive()){ $("#recStart").disabled=false; msg.textContent="Не удалось включить микрофон/камеру ("+e.name+"). Запись не началась — можно выбрать файл."; }
      return;
    }
    if(!alive()){ stream.getTracks().forEach(t=>t.stop()); studio.pending=false; return; }  /* page changed while asking */
    studio.stream=stream;
    const myStream=stream, myChunks=[];
    let mr;
    try{ mr=new MediaRecorder(stream); }
    catch(e){
      myStream.getTracks().forEach(t=>{ try{t.stop()}catch(_){} });
      if(studio.stream===myStream) studio.stream=null;
      studio.pending=false;
      if(alive()){ $("#recStart").disabled=false; msg.textContent="Запись в этом браузере недоступна. Можно выбрать собственный файл рядом."; }
      return;
    }
    studio.mr=mr;
    mr.ondataavailable=e=>{ if(studio.generation===gen && studio.mr===mr && e.data && e.data.size) myChunks.push(e.data); };
    mr.onstop=()=>{
      /* scoped to THIS recorder/stream: never touch a newer session's shared state */
      myStream.getTracks().forEach(t=>{ try{t.stop()}catch(_){} });
      if(studio.stream===myStream) studio.stream=null;
      if(studio.mr===mr) studio.mr=null;
      if(studio.generation!==gen) return;
      studio.pending=false;
      if(!alive()) return;                            /* DOM gone: nothing to update */
      $("#recInd").textContent="Запись остановлена"; $("#recStop").disabled=true; $("#recStart").disabled=false;
      const blob=new Blob(myChunks,{type:mr.mimeType||"audio/webm"});
      if(!blob.size){ $("#recMsg").textContent="Запись получилась пустой. Попробуйте ещё раз."; return; }
      const url=URL.createObjectURL(blob); studio.objectUrls.push(url);
      const isV=blob.type.includes("video");
      $("#recOut").innerHTML=(isV?`<video controls src="${url}"></video>`:`<audio controls src="${url}"></audio>`)+
        `<p><a class="btn small" href="${url}" download="souls-of-muse-recording.webm">Скачать запись</a></p><p>Запись хранится только здесь, пока вы её не скачали.</p>`;
    };
    try{ mr.start(); }
    catch(e){
      const msgEl=$("#recMsg"), startEl=$("#recStart");
      cleanupStudio();
      gen = studio.generation;   /* resync this page's binder after in-page cleanup */
      if(msgEl && msgEl.isConnected) msgEl.textContent="Не удалось начать запись. Можно выбрать собственный файл рядом.";
      if(startEl && startEl.isConnected) startEl.disabled=false;
      return;
    }
    if(alive()){ $("#recInd").innerHTML=`<span class="rec-dot" aria-hidden="true"></span> Идёт запись`; $("#recStop").disabled=false; msg.textContent=""; }
  };
  $("#recStop").onclick=()=>{ if(studio.mr && studio.mr.state!=="inactive"){ try{studio.mr.stop()}catch(e){ cleanupStudio(); gen = studio.generation; } } };
  $("#fileIn").addEventListener("change",e=>{ const f=e.target.files[0]; if(!f||!alive()) return;
    const url=URL.createObjectURL(f); studio.objectUrls.push(url);
    $("#filePrev").innerHTML=(f.type.startsWith("video")?`<video controls src="${url}"></video>`:`<audio controls src="${url}"></audio>`)+
      `<p>${esc(f.name)} · ${(f.size/1048576).toFixed(2)} МБ · файл остаётся на этом устройстве</p>`; });
  $("#saveDraft").onclick=()=>{ try{
      localStorage.setItem("som_local_draft", JSON.stringify({title:$("#metaT").value,desc:$("#metaD").value,vis:$("#metaV").value,pubConsent:$("#pubConsent").checked}));
      $("#draftMsg").textContent="Черновик сохранён на этом устройстве. Это ещё не публикация.";
    }catch(e){ $("#draftMsg").textContent="Сохранить черновик в этом браузере не удалось."; } };
  $("#bpm").addEventListener("input",e=>{ $("#bpmVal").textContent=e.target.value;
    if(studio.metroTimer){ clearInterval(studio.metroTimer); studio.metroTimer=setInterval(clickMetro, 60000/(+e.target.value)); } });
  const clickMetro=()=>{ const c=studio.metroCtx; if(!c) return;
    const o=c.createOscillator(), g=c.createGain(), t=c.currentTime;
    o.frequency.value=1200; g.gain.setValueAtTime(.25,t); g.gain.exponentialRampToValueAtTime(.0001,t+.06);
    o.connect(g).connect(c.destination); o.start(t); o.stop(t+.07); };
  $("#metroBtn").onclick=()=>{
    if(studio.metroTimer){ clearInterval(studio.metroTimer); studio.metroTimer=null; $("#metroBtn").textContent="Включить метроном"; return; }
    const AC=window.AudioContext||window.webkitAudioContext; if(!AC) return;
    studio.metroCtx = studio.metroCtx || new AC();
    if(studio.metroCtx.state==="suspended") studio.metroCtx.resume();
    $("#metroBtn").textContent="Выключить метроном"; clickMetro();
    studio.metroTimer=setInterval(clickMetro, 60000/(+$("#bpm").value));
  };
  $("#sessBtn").onclick=()=>{ if(!alive()) return; const d=document.createElement("div"); d.className="item";
    d.innerHTML=`<strong>${esc($("#sessT").value||"Встреча")}</strong><p>${esc($("#sessEx").value)} · ${esc($("#sessR").value)} · темп ${esc($("#bpm").value)} BPM</p><p>План встречи на этом устройстве.</p>`;
    $("#sessOut").prepend(d); };
}

/* ---------- router with unified page cleanup ---------- */
let focusTabOnRender=false;
function cleanupPage(){ stopPlay(); cleanupStudio(); }
const routes=[[/^#?\/?$/,vHome,"ceremony"],[/^#\/convention$/,vConvention,"ceremony"],[/^#\/welcome$/,vWelcome,"ceremony"],
 [/^#\/leagues$/,vLeagues,"workshop"],[/^#\/league\/([^/]+)(?:\/([^/]+))?$/,m=>vLeague(decodeURIComponent(m[1]), m[2]||"topics"),"workshop"],
 [/^#\/cabinet\/(student|teacher|listener)$/,m=>vCabinet(m[1]),"workshop"],[/^#\/studio$/,vStudio,"workshop"]];
function render(){
  cleanupPage();
  const h=location.hash||"#/";
  for(const[re,fn,mode] of routes){ const m=h.match(re); if(m){
    document.body.className=mode;
    document.body.innerHTML=fn(m);
    bindCommon();
    if(h==="#/convention") bindConvention();
    else if(h==="#/welcome") bindWelcome();
    else if(h==="#/leagues") bindLeagues();
    else if(h.startsWith("#/league/")){ const seg=h.slice("#/league/".length).split("/"); bindLeague(seg[1]||"topics", seg[0]); }
    else if(h==="#/studio") bindStudio();
    window.scrollTo(0,0);
    if(focusTabOnRender){ focusTabOnRender=false;
      const sel=document.querySelector("[data-tab][aria-selected=\"true\"]");
      if(sel){ sel.focus({preventScroll:true}); return; } }
    const mm=$("#main"); if(mm) mm.focus({preventScroll:true});
    return; } }
  location.hash="#/";
}
window.addEventListener("hashchange",render);
window.addEventListener("pagehide",cleanupPage);
document.addEventListener("keydown",e=>{ if(e.key==="Escape"){ const d=$("#dlg"); if(d&&d.open) d.close(); } });
render();
