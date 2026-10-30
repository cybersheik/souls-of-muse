"use strict";
/* Souls of Muse — Portal P0.1 strings & demo data.
   Single strings file per DW1 brief (AI3-928): all user-facing text for
   Welcome (02), Personal space (03) and Components (04) lives here so the
   role vocabulary (Maestro / Artist / Admirer, session / встреча) can be
   replaced in one place. Extracted mechanically from
   'Souls of Muse Portal P0.1.dc.html' (Project archive, 31.10.2026). */
const SIGS = {
  latin: { name: 'Lina Khairullina', file: 'uploads/sig-latin.png', genre: 'Hip-hop · 88 bpm · 4/4', keys: ['lina khairullina', 'khairullina'], bpm: 88,
    seq: [[60,.5],[67,.5],[64,.5],[65,.5],[74,.75],[62,.25],[65,.5],[67,1],[67,.5],[71,.5],[79,.25],[76,.75],[74,.25],[76,.5],[71,.5],[67,.5],[69,1]] },
  cyrillic: { name: 'Айдар Кожахметов', file: 'uploads/sig-cyrillic.png', genre: 'Swing · 138 bpm · 4/4', keys: ['айдар кожахметов', 'кожахметов', 'aidar kozhakhmetov'], bpm: 138, swing: true,
    seq: [[67,.5],[74,.5],[74,1],[69,.5],[74,1.5],[74,.5],[69,1],[69,.5],[64,.5],[71,.5],[69,1],[74,.5],[72,1],[64,.5],[62,1],[64,.5],[67,.5],[66,1.5]] },
  viet: { name: 'Nguyễn Thị Mai', file: 'uploads/sig-viet.png', genre: 'Waltz · 150 bpm · 3/4', keys: ['nguyen thi mai', 'mai'], bpm: 150,
    seq: [[67,1],[67,1],[67,1],[62,1],[64,1],[67,2],[64,1],[71,.5],[71,1.5],[64,1],[69,1],[71,2],[71,3]] },
  korean: { name: '김민지', file: 'uploads/sig-korean.png', genre: 'Waltz · 150 bpm · 3/4', keys: ['김민지', 'kim minji', 'minji'], bpm: 150,
    seq: [[69,3],[69,1],[64,1],[71,1],[71,3]] },
  japanese: { name: 'さくら', file: 'uploads/sig-japanese.png', genre: 'Hip-hop · 88 bpm · 4/4', keys: ['さくら', 'sakura'], bpm: 88,
    seq: [[71,1],[67,.5],[69,2],[67,.5]] },
  short: { name: 'Haydn', file: 'uploads/sig-short.png', genre: 'Pop · 108 bpm · 4/4', keys: ['haydn'], bpm: 108,
    seq: [[71,.5],[67,.5],[74,.5],[74,.25],[76,2],[74,1.5]] },
};
const SKETCH = { bpm: 96, seq: [[53,.5],[57,.5],[60,.5],[65,.5],[48,.5],[52,.5],[55,.5],[60,1.5],[53,.5],[57,.5],[60,.5],[65,.5],[48,.5],[55,.5],[60,1.5]] };
const BREATH = { bpm: 72, seq: [[64,1],[65,1],[67,2],[67,1],[65,1],[64,2]] };

const T = {
  en: {
    navConv: 'Convention', navLeagues: 'Leagues', navSpace: 'My space',
    heroKicker: 'Convention of the Keepers of Live Music',
    heroTitle: 'Type your name. Hear it as music.',
    heroSub: 'Every member signs with their name written on a staff. A free association of musicians keeping live music alive. MUSE only connects people.',
    nameLabel: 'Your name', namePh: 'Type your name', tryLabel: 'Try', listen: 'Listen', listenHint: 'Press play to hear it',
    sign: 'Sign the Convention', signVia: 'Signed from your Facebook or Instagram account',
    chipComposing: 'Your melody is composed when you sign', chipEmpty: 'Type a name to see it on the staff',
    readAll: 'Read the full Convention', collapse: 'Collapse',
    leaguesTitle: 'Seven Leagues', leaguesNote: 'Each League chooses its own emblem.',
    footer: 'Free and non-commercial. MUSE connects people. It never replaces a Maestro.',
    wKicker: 'Welcome to Souls of Muse', wTitle: 'Lina, this is your name in music.', wSub: 'You signed the Convention. These gifts are yours.',
    listenYours: 'Listen to your signature',
    gCard: 'Your card', gMedal: 'Your medal', gVoice: 'Your voice',
    cardKicker: 'Keeper of Live Music', cardSigned: 'Signed 30 Oct 2026 · Instagram', cardLeague: 'League: to choose',
    medalName: 'Keeper of Live Music', medalFor: 'For taking part.', playful: 'Playful', classic: 'Classic', styleLabel: 'Style is yours',
    voiceTitle: 'A voice in your League', voiceBody: 'Your signature is your vote. Members decide their League’s emblem, events and rules together.', voiceBodyShort: 'Your signature is your vote in the League.',
    chipNotOpen: 'First vote not open yet',
    cta: 'Choose your League and role', ctaTail: 'enter your space',
    originQ: 'Where does my signature come from?',
    greet: 'Good evening, Lina', dateLine: 'Wed 30 Oct · 17:20', roleHint: 'One space. Switch your context.',
    roleT: 'Maestro', roleS: 'Artist', roleL: 'Admirer',
    today: 'Today', mode: 'How do you join?', indiv: 'One-to-one', group: 'In a circle',
    museTitle: 'MUSE · mediator', museRule: 'Translates and suggests. People decide.',
    league: 'My League', people: 'People', events: 'Events', recs: 'My recordings',
    chipVote: 'League vote not open yet', chipEmptyRecs: 'No recordings yet. Saved live sets appear here.',
  },
  ru: {
    navConv: 'Конвенция', navLeagues: 'Лиги', navSpace: 'Моё пространство',
    heroKicker: 'Конвенция хранителей живой музыки',
    heroTitle: 'Напишите имя. Услышьте его музыкой.',
    heroSub: 'Каждый участник подписывается своим именем, записанным нотами. Свободное объединение музыкантов, хранящих живую музыку. MUSE лишь соединяет людей.',
    nameLabel: 'Ваше имя', namePh: 'Введите имя', tryLabel: 'Например', listen: 'Слушать', listenHint: 'Нажмите, чтобы услышать',
    sign: 'Подписать Конвенцию', signVia: 'Подпись через ваш аккаунт Facebook или Instagram',
    chipComposing: 'Мелодия сочиняется при подписании', chipEmpty: 'Введите имя, чтобы увидеть его нотами',
    readAll: 'Читать Конвенцию целиком', collapse: 'Свернуть',
    leaguesTitle: 'Семь Лиг', leaguesNote: 'Каждая Лига выбирает свою эмблему.',
    footer: 'Бесплатно и некоммерчески. MUSE соединяет людей и никогда не заменяет Маэстро.',
    wKicker: 'Добро пожаловать в Souls of Muse', wTitle: 'Лина, так звучит ваше имя.', wSub: 'Вы подписали Конвенцию. Эти подарки — ваши.',
    listenYours: 'Послушать свою подпись',
    gCard: 'Ваша карточка', gMedal: 'Ваша медаль', gVoice: 'Ваш голос',
    cardKicker: 'Хранитель живой музыки', cardSigned: 'Подписано 30 окт 2026 · Instagram', cardLeague: 'Лига: выбрать',
    medalName: 'Хранитель живой музыки', medalFor: 'За участие.', playful: 'Игривый', classic: 'Классика', styleLabel: 'Стиль — ваш выбор',
    voiceTitle: 'Голос в вашей Лиге', voiceBody: 'Ваша подпись — ваш голос. Участники вместе решают эмблему, события и правила своей Лиги.', voiceBodyShort: 'Ваша подпись — ваш голос в Лиге.',
    chipNotOpen: 'Первое голосование ещё не открыто',
    cta: 'Выберите Лигу и роль', ctaTail: 'войдите в своё пространство',
    originQ: 'Откуда моя подпись?',
    greet: 'Добрый вечер, Лина', dateLine: 'Ср 30 окт · 17:20', roleHint: 'Одно пространство. Меняйте контекст.',
    roleT: 'Маэстро', roleS: 'Артист', roleL: 'Ценитель',
    today: 'Сегодня', mode: 'Как подключиться?', indiv: 'Один на один', group: 'В кругу',
    museTitle: 'MUSE · посредник', museRule: 'Переводит и подсказывает. Решают люди.',
    league: 'Моя Лига', people: 'Люди', events: 'События', recs: 'Мои записи',
    chipVote: 'Голосование Лиги ещё не открыто', chipEmptyRecs: 'Записей пока нет. Сохранённые живые выступления появятся здесь.',
  },
};


const P01_LEAGUES = [
  ['ph-guitar', 'Guitar', 'Гитара', 'acoustic · electric · bass', 'акустика · электро · бас'],
  ['ph-piano-keys', 'Keys', 'Клавишные', 'piano · organ · synth', 'фортепиано · орган · синт'],
  ['ph-wind', 'Winds', 'Духовые', 'flute · sax · brass', 'флейта · сакс · медь'],
  ['ph-metronome', 'Drums', 'Ударные', 'kit · hand · percussion', 'установка · перкуссия'],
  ['ph-waveform', 'Electronic', 'Электроника', 'production · live sets', 'продакшн · лайв-сеты'],
  ['ph-microphone-stage', 'Vocal', 'Вокал', 'solo · choir', 'соло · хор'],
  ['ph-feather', 'Folk', 'Фолк', 'dombra · kobza · koto', 'домбра · кобза · кото'],
];

const ORIGIN = {
  en: [['Letters → pitches', 'Each letter of your name lands on a note of the staff.'], ['Syllables → rhythm', 'The way your name is spoken sets the length of each note.'], ['Style & tempo', 'MUSE picks a style and tempo that suit the sound. For you: hip-hop at 88.']],
  ru: [['Буквы → высоты', 'Каждая буква имени становится нотой на нотном стане.'], ['Слоги → ритм', 'Как произносится имя, так и задаются длительности нот.'], ['Стиль и темп', 'MUSE подбирает стиль и темп под звучание имени. Для вас — хип-хоп, темп 88.']],
};

const ROLE = {
  student: {
    en: { today: { kicker: 'Guitar · Session 3 · with Ramires95', title: 'F → C changes, strumming in 4/4', meta: 'Today · 19:00–19:45', chip: 'Starts in 1 h 40 min', chipIcon: 'ph-clock', peopleNote: 'Ramires95 + 3 artists', action: 'Enter session' },
      modes: { indiv: 'One-to-one with Ramires95 · 30 min', group: 'With Aidar, Mai and Minji · 45 min' },
      muse: { intro: 'Ramires95 left you a note after Session 2, in Portuguese. Translated:', quote: '“Slow the F → C change down to 60 bpm. Lift all fingers together, then land them at once.”', meta: 'Session 2 · clean 6/10 · on beat 81%', a1: 'Practise at 60 bpm', a2: 'Reply to Ramires95' },
      league: { name: 'Guitar League', events: [['Oct', '31', 'Open jam, Lisbon + online', 'Thu · 20:00 · 41 going'], ['Nov', '2', 'Fingerstyle circle with Minji', 'Sat · 18:00 · 12 seats']] },
      recsTitle: 'My recordings', place: 'You: Artist · session 3 of 8 · a voice in League votes',
      recs: [['sig', 'My signature', 'Hip-hop · 88 bpm · 0:07'], ['sk', 'Session 2 · F → C change', '30 Oct · 0:42', 'Waiting for Maestro’s OK'], ['sk', 'Practice · Am–F–C–G', '29 Oct · 1:15']] },
    ru: { today: { kicker: 'Гитара · Встреча 3 · с Ramires95', title: 'Смена F → C, бой на 4/4', meta: 'Сегодня · 19:00–19:45', chip: 'Через 1 ч 40 мин', chipIcon: 'ph-clock', peopleNote: 'Ramires95 и ещё 3 артиста', action: 'Войти во встречу' },
      modes: { indiv: 'Один на один с Ramires95 · 30 мин', group: 'С Айдаром, Май и Минджи · 45 мин' },
      muse: { intro: 'Ramires95 оставил вам заметку после встречи 2, на португальском. Перевод:', quote: '«Замедлите смену F → C до 60 ударов. Поднимайте все пальцы вместе и ставьте их разом».', meta: 'Встреча 2 · чисто 6/10 · в долю 81%', a1: 'Заниматься на 60', a2: 'Ответить Ramires95' },
      league: { name: 'Лига гитары', events: [['окт', '31', 'Открытый джем, Лиссабон + онлайн', 'Чт · 20:00 · идут 41'], ['ноя', '2', 'Фингерстайл-круг с Минджи', 'Сб · 18:00 · 12 мест']] },
      recsTitle: 'Мои записи', place: 'Вы: Артист · встреча 3 из 8 · голос в решениях Лиги',
      recs: [['sig', 'Моя подпись', 'Хип-хоп · 88 · 0:07'], ['sk', 'Встреча 2 · смена F → C', '30 окт · 0:42', 'Ждёт одобрения Маэстро'], ['sk', 'Практика · Am–F–C–G', '29 окт · 1:15']] },
    people: [['RA', 'Ramires95', 'Maestro', 'Маэстро', 'PT · EN'], ['АК', 'Айдар Кожахметов', 'Artist', 'Артист', 'KK · RU'], ['NM', 'Nguyễn Thị Mai', 'Artist', 'Артист', 'VI'], ['김', '김민지', 'Maestro · fingerstyle', 'Маэстро · фингерстайл', 'KO · EN']],
    todayPeople: ['RA', 'АК', 'NM', '김'], lesson: true,
  },
  teacher: {
    en: { today: { kicker: 'Vocal · Session 1 · you lead', title: 'Breath and the first phrase', meta: 'Today · 21:00–21:45', chip: 'Starts in 3 h 40 min', chipIcon: 'ph-clock', peopleNote: 'Sakura, Haydn, Aidar · all confirmed', action: 'Open session' },
      modes: { indiv: 'One artist at a time · 30 min', group: 'Sakura, Haydn and Aidar · 45 min' },
      muse: { intro: 'Sakura wrote to you in Japanese. Translated:', quote: '“Could I try one session one-to-one first? I’m shy to sing in a circle.”', meta: 'From Session 0 · Sakura clean 7/10 · Haydn 5/10 · Aidar 8/10', a1: 'Offer one-to-one Sat 10:30', a2: 'Reply, MUSE translates' },
      league: { name: 'Vocal League', events: [['Nov', '1', 'Choir warm-up for new Maestros', 'Fri · 19:00 · online'], ['Nov', '9', 'Open mic, Almaty + online', 'Sat · 20:00 · 28 going']] },
      recsTitle: 'Artists’ recordings', place: 'You: Maestro · 3 artists · a voice in League votes',
      recs: [['br', 'Sakura · first phrase, practice', '30 Oct · 0:52', 'Waiting for your OK'], ['br', 'Haydn · breath on 4 counts', '29 Oct · 0:41', 'Waiting for your OK'], ['br', 'Aidar · first phrase', '29 Oct · 0:47']] },
    ru: { today: { kicker: 'Вокал · Встреча 1 · вы ведёте', title: 'Дыхание и первая фраза', meta: 'Сегодня · 21:00–21:45', chip: 'Через 3 ч 40 мин', chipIcon: 'ph-clock', peopleNote: 'Сакура, Haydn, Айдар · все подтвердили', action: 'Открыть встречу' },
      modes: { indiv: 'По одному артисту · 30 мин', group: 'Сакура, Haydn и Айдар · 45 мин' },
      muse: { intro: 'Сакура написала вам по-японски. Перевод:', quote: '«Можно сначала одну встречу один на один? Мне неловко петь в кругу».', meta: 'Встреча 0 · Сакура чисто 7/10 · Haydn 5/10 · Айдар 8/10', a1: 'Предложить один на один, сб 10:30', a2: 'Ответить, MUSE переведёт' },
      league: { name: 'Лига вокала', events: [['ноя', '1', 'Распевка хора для новых маэстро', 'Пт · 19:00 · онлайн'], ['ноя', '9', 'Открытый микрофон, Алматы + онлайн', 'Сб · 20:00 · идут 28']] },
      recsTitle: 'Записи артистов', place: 'Вы: Маэстро · 3 артиста · голос в решениях Лиги',
      recs: [['br', 'Сакура · первая фраза, практика', '30 окт · 0:52', 'Ждёт вашего одобрения'], ['br', 'Haydn · дыхание на 4 счёта', '29 окт · 0:41', 'Ждёт вашего одобрения'], ['br', 'Айдар · первая фраза', '29 окт · 0:47']] },
    people: [['さ', 'さくら', 'Artist', 'Артист', 'JA'], ['HA', 'Haydn', 'Artist', 'Артист', 'EN · DE'], ['АК', 'Айдар Кожахметов', 'Artist', 'Артист', 'KK · RU'], ['OL', 'Olga Petrenko', 'Maestro · choir', 'Маэстро · хор', 'UK · RU']],
    todayPeople: ['さ', 'HA', 'АК'], lesson: true,
  },
  listener: {
    en: { today: { kicker: 'Folk League · small concert, online', title: 'Aidar Kozhakhmetov · dombra, kyui of the steppe', meta: 'Today · 20:30 · online · 64 seats', chip: 'Seat held · confirm by 19:30', chipIcon: 'ph-seal-question', peopleNote: 'Aidar + 2 guest players', action: 'Confirm my seat' },
      muse: { intro: 'Aidar introduces each kyui in Kazakh. I’ll subtitle the intros in English during the evening.', quote: '“A kyui is a story told without words. Each one has a title and a legend.”', meta: 'Subtitles: English · Kazakh original', a1: 'Keep subtitles on', a2: 'Ask Aidar a question' },
      league: { name: 'Folk League', events: [['Oct', '31', 'Open jam near you · Lisbon, Café Ritornello', 'Thu · 20:00 · 2.1 km · 41 going'], ['Nov', '3', 'Small concert online · koto and kobza', 'Sun · 19:30 · 48 seats left']] },
      recsTitle: 'Shared for listening', place: 'You: Admirer · since 30 Oct · 3 evenings · a voice in League votes',
      recs: [['sk', 'Aidar · kyui “Adai”, live', 'Aidar · 4:12'], ['br', 'Sakura · koto miniature', 'Sakura · 2:30'], ['sk', 'Open jam Lisbon · last week', 'Taras · 18:05']] },
    ru: { today: { kicker: 'Лига фолка · камерный концерт, онлайн', title: 'Айдар Кожахметов · домбра, кюи степи', meta: 'Сегодня · 20:30 · онлайн · 64 места', chip: 'Место за вами · подтвердить до 19:30', chipIcon: 'ph-seal-question', peopleNote: 'Айдар и 2 гостя', action: 'Подтвердить место' },
      muse: { intro: 'Айдар представляет каждый кюй по-казахски. Я дам субтитры к вступлениям на русском.', quote: '«Кюй — это история без слов. У каждого есть название и легенда».', meta: 'Субтитры: русский · оригинал на казахском', a1: 'Оставить субтитры', a2: 'Спросить Айдара' },
      league: { name: 'Лига фолка', events: [['окт', '31', 'Открытый джем рядом · Лиссабон, Café Ritornello', 'Чт · 20:00 · 2,1 км · идут 41'], ['ноя', '3', 'Камерный концерт онлайн · кото и кобза', 'Вс · 19:30 · осталось 48 мест']] },
      recsTitle: 'Открыто для прослушивания', place: 'Вы: Ценитель · с 30 окт · 3 вечера · голос в решениях Лиги',
      recs: [['sk', 'Айдар · кюй «Адай», живьём', 'Айдар · 4:12'], ['br', 'Сакура · миниатюра на кото', 'Сакура · 2:30'], ['sk', 'Открытый джем, Лиссабон · прошлая неделя', 'Тарас · 18:05']] },
    people: [['АК', 'Айдар Кожахметов', 'Maestro · dombra', 'Маэстро · домбра', 'KK · RU'], ['さ', 'さくら', 'koto', 'кото', 'JA'], ['TB', 'Taras Bondar', 'Maestro · kobza', 'Маэстро · кобза', 'UK · EN'], ['NM', 'Nguyễn Thị Mai', 'Admirer', 'Ценитель', 'VI']],
    todayPeople: ['АК', 'さ', 'TB'], lesson: false,
  },
};


const P01Strings = { SIGS, T, ORIGIN, LEAGUES: P01_LEAGUES, ROLE };
if (typeof window !== "undefined") window.P01Strings = P01Strings;
if (typeof module !== "undefined") module.exports = P01Strings;
