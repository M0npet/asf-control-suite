(() => {
  'use strict';

  // Same persistence key used by the pinned ASF-ui (src/utils/storage.js + i18n plugin).
  const ASF_LOCALE_KEY = 'asf-ui:locale';
  const DEFAULT_LOCALE = 'en-US';
  const SUPPORTED = Object.freeze(['en-US', 'uk-UA']);

  const UK = Object.freeze({
    'Secure control plane': 'Захищена панель керування',
    'Connect to ASF': 'Підключення до ASF',
    'Enter the existing ASF IPC password. It is kept only in page memory and is lost on refresh, lock, or tab close.': 'Введіть чинний пароль ASF IPC. Він зберігається лише в цій вкладці браузера та очищається, коли сесія блокується.',
    'IPC password': 'Пароль IPC',
    'Show password': 'Показати пароль',
    'Hide password': 'Сховати пароль',
    'Show': 'Показати',
    'Hide': 'Сховати',
    'Connect': 'Підключитися',
    'HTTPS/Tailscale remains the outer transport boundary': 'HTTPS/Tailscale залишається зовнішнім рівнем захисту транспорту',
    'Primary navigation': 'Основна навігація',
    'Dashboard': 'Огляд',
    'Accounts': 'Облікові записи',
    'Playtime Goals': 'Цілі ігрового часу',
    'Security': 'Безпека',
    'System': 'Система',
    'Advanced': 'Розширене',
    'Lock session': 'Заблокувати сесію',
    'Refresh current view': 'Оновити поточний розділ',
    'Refresh': 'Оновити',
    'checking': 'перевірка',
    'connected': 'підключено',
    'offline': 'офлайн',
    'locked': 'заблоковано',
    'error': 'помилка',
    'restarting': 'перезапуск',
    'stopped': 'зупинено',
    'Dismiss': 'Закрити',
    'Close dialog': 'Закрити діалог',
    'Cancel': 'Скасувати',
    'Confirm': 'Підтвердити',
    'Type ': 'Введіть ',
    ' to continue': ' для продовження',
    'Live overview of ASF, accounts and runtime health.': 'Оперативний огляд ASF, облікових записів і стану середовища.',
    'Create, inspect and control ASF bot accounts.': 'Створення, перегляд і керування обліковими записами ботів ASF.',
    'Manage finite and unlimited playtime goals safely.': 'Безпечне керування обмеженими та безлімітними цілями ігрового часу.',
    'Session controls and the authentication boundary.': 'Керування сесією та межею автентифікації.',
    'Runtime health, modules and native ASF process actions.': 'Стан середовища, модулі та штатні дії з процесом ASF.',
    'Architecture, pinned targets and native API access.': 'Архітектура, зафіксовані версії та доступ до штатного API.',

    'Needs input': 'Потрібне введення',
    'Connected': 'Підключено',
    'Connecting': 'Підключення',
    'Stopped': 'Зупинено',
    'no nickname': 'без псевдоніма',
    'unknown': 'невідомо',
    'cards farming': 'вибивання карток',
    'farmer paused': 'фармер призупинений',
    'farmer idle': 'фармер неактивний',
    'enabled': 'увімкнено',
    'disabled': 'вимкнено',
    'Open': 'Відкрити',
    'Goals': 'Цілі',
    'Stop': 'Зупинити',
    'Start': 'Запустити',
    'Pause': 'Призупинити',
    'Resume': 'Відновити',
    'Rename': 'Перейменувати',
    'Delete': 'Видалити',
    'No ASF accounts yet': 'Облікових записів ASF ще немає',
    'Create one from the Accounts page.': 'Створіть перший у розділі «Облікові записи».',
    'No account selected': 'Обліковий запис не вибрано',
    'Choose an account above.': 'Виберіть обліковий запис вище.',
    'Account unavailable': 'Обліковий запис недоступний',
    'Refresh the account list.': 'Оновіть список облікових записів.',
    'Action required.': 'Потрібна дія.',
    'Steam / ASF input': 'Введення Steam / ASF',
    'Enter requested value': 'Введіть потрібне значення',
    'Send securely': 'Надіслати безпечно',
    'No interactive input is required from this account.': 'Для цього облікового запису зараз не потрібне інтерактивне введення.',
    'Account workspace · native ASF state': 'Робоча область облікового запису · штатний стан ASF',
    'Open goals': 'Відкрити цілі',
    'Disable config': 'Вимкнути конфігурацію',
    'Enable config': 'Увімкнути конфігурацію',
    'Keep running': 'Підтримувати запущеним',
    'Playing': 'Запуск ігор',
    'possible': 'можливий',
    'blocked': 'заблокований',
    'CardsFarmer': 'CardsFarmer',
    'active': 'активний',
    'paused': 'призупинений',
    'idle': 'неактивний',
    'Authenticator': 'Автентифікатор',
    'yes': 'так',
    'no': 'ні',

    'Accounts': 'Облікові записи',
    'Connected': 'Підключено',
    'Cards farming': 'Вибивання карток',
    'Control uptime': 'Час роботи Control',
    'native CardsFarmer': 'штатний CardsFarmer',
    'Control plane is healthy and no account is waiting for input.': 'Панель керування працює нормально, жоден обліковий запис не очікує введення.',
    'Current ASF bots and the actions that need attention.': 'Поточні боти ASF і дії, що потребують уваги.',
    'Manage': 'Керувати',
    'Runtime': 'Середовище виконання',
    'Read-only host and ASF health.': 'Стан хоста й ASF лише для читання.',
    'healthy': 'справно',
    'ASF API': 'API ASF',
    'authenticated and responding': 'автентифіковано, відповідає',
    'Framework': 'Платформа',
    'Operating system': 'Операційна система',
    'Managed memory': 'Керована пам’ять',
    'Disk free': 'Вільно на диску',

    'Registered accounts': 'Зареєстровані облікові записи',
    'Add account': 'Додати обліковий запис',
    'Credentials go directly to native ASF APIs.': 'Облікові дані передаються безпосередньо до штатного API ASF.',
    'ASF bot name': 'Ім’я бота ASF',
    'Steam login': 'Логін Steam',
    'Steam password': 'Пароль Steam',
    'The password is AES-encrypted by ASF before BotConfig is written.': 'Пароль шифрується ASF за допомогою AES до запису BotConfig.',
    'Create account': 'Створити обліковий запис',
    'AccountManager never receives or stores the Steam password.': 'AccountManager ніколи не отримує і не зберігає пароль Steam.',
    'Defaults for new accounts': 'Значення за замовчуванням для нових облікових записів',
    'advanced': 'розширено',
    'Defaults JSON': 'JSON значень за замовчуванням',
    'Validate & save defaults': 'Перевірити й зберегти',
    'credentials and security fields': 'облікові дані та поля безпеки',
    'Blocked keys:': 'Заблоковані ключі:',

    'No managed games': 'Немає керованих ігор',
    'Select games above and save the configuration.': 'Виберіть ігри вище та збережіть конфігурацію.',
    'unlimited': 'безліміт',
    'allowed': 'дозволено',
    'base': 'базове',
    'custom': 'власне',
    'unset': 'не задано',
    'allow': 'дозволити',
    'deny': 'заборонити',
    'No managed Family View entries': 'Немає керованих записів Family View',
    'Nothing to restore or override right now.': 'Зараз немає чого відновлювати або перевизначати.',
    'Available': 'Доступність',
    'Enabled': 'Увімкнено',
    'Allowed': 'Дозволено',
    'Blocked': 'Заблоковано',
    'No account available': 'Немає доступного облікового запису',
    'Add an ASF account first.': 'Спочатку додайте обліковий запис ASF.',
    'PlaytimeGoals is unavailable:': 'PlaytimeGoals недоступний:',
    'Library is empty': 'Бібліотека порожня',
    'Reconnect the account and refresh.': 'Перепідключіть обліковий запис і оновіть дані.',
    'ASF account': 'Обліковий запис ASF',
    'managed': 'під керуванням',
    'Active batch': 'Активний пакет',
    'queued by priority': 'черга за пріоритетом',
    'Library': 'Бібліотека',
    'own': 'власні',
    'family': 'сімейні',
    'Free / excluded': 'Безкоштовні / виключені',
    'free selectable · excluded blocked': 'безкоштовні можна вибрати · виключені заблоковані',
    'Recovery': 'Відновлення',
    'Family View journal': 'журнал Family View',
    'Configuration': 'Налаштування',
    'PlaytimeGoals remains the only owner of managed GamesPlayed state.': 'PlaytimeGoals залишається єдиним власником керованого стану GamesPlayed.',
    'PlaytimeGoals enabled': 'PlaytimeGoals увімкнено',
    'Batch size': 'Розмір пакета',
    'Family View writes': 'Зміни Family View',
    'Blank target means unlimited. Enabling PlaytimeGoals clears native ASF idle-game fields to prevent competing GamesPlayed owners.': 'Порожня ціль означає безліміт. Під час увімкнення PlaytimeGoals штатні поля простою ASF очищаються, щоб два компоненти не керували GamesPlayed одночасно.',
    'Search by game name or AppID': 'Пошук за назвою гри або AppID',
    'Search games': 'Пошук ігор',
    'Filter by source': 'Фільтр за джерелом',
    'All sources': 'Усі джерела',
    'OWN': 'ВЛАСНА',
    'FAMILY': 'СІМЕЙНА',
    'FREE': 'БЕЗКОШТОВНА',
    'EXCLUDED': 'ВИКЛЮЧЕНА',
    'Save goals': 'Зберегти цілі',
    'Managed status': 'Стан керованих ігор',
    'Effective credit, targets and queue state.': 'Врахований час, цілі та стан черги.',
    'Family View': 'Family View',
    'Current parental state for managed applications.': 'Поточний стан батьківського контролю для керованих застосунків.',
    'available': 'доступно',
    'unavailable': 'недоступно',
    'not exposed by runtime': 'не надається середовищем виконання',
    'availability unknown': 'доступність невідома',
    'queue': 'черга',
    'queued': 'у черзі',
    'family-not-shareable': 'сімейний доступ заборонено',
    'family-copy-busy': 'сімейна копія зайнята',
    'family-availability-unknown': 'доступність сімейної копії невідома',
    'parental-blocked': 'заблоковано Family View',
    'asf-farming': 'ASF вибиває картки',
    'asf-paused': 'фармер ASF призупинений',
    'free-license-pending': 'отримання безкоштовної ліцензії',
    'free-license-claim-failed': 'не вдалося отримати ліцензію',
    'Target hours for': 'Цільові години для',

    'Authentication boundary': 'Межа автентифікації',
    'Defense in depth around ASF IPC.': 'Багаторівневий захист ASF IPC.',
    'HTTPS / Tailscale': 'HTTPS / Tailscale',
    'Transport and network reachability remain outside ASF.': 'Транспорт і мережевий доступ залишаються поза межами ASF.',
    'ASF IPCPassword': 'ASF IPCPassword',
    'Every /Api request from this UI carries the native Authentication header.': 'Кожен запит /Api з цього інтерфейсу містить штатний заголовок Authentication.',
    'Tab-scoped session': 'Сесія в межах вкладки',
    'The IPC password is kept only in page memory and is lost on refresh, lock, or tab close.': 'Пароль IPC зберігається лише в пам’яті сторінки та втрачається після оновлення, блокування або закриття вкладки.',
    'Session lock': 'Блокування сесії',
    'Protect an unattended browser tab.': 'Захист вкладки браузера, залишеної без нагляду.',
    'Auto-lock after inactivity': 'Автоблокування після бездіяльності',
    'Never in this tab': 'Ніколи в цій вкладці',
    'Activity resets the timer. “Never” applies only to this tab.': 'Будь-яка активність скидає таймер. «Ніколи» діє лише для цієї вкладки.',
    'Lock now': 'Заблокувати зараз',
    'Security invariants': 'Гарантії безпеки',
    'What Control Suite 1.0 intentionally does not expose.': 'Що Control Suite 1.0 принципово не відкриває.',
    'No arbitrary shell or process execution endpoint.': 'Немає API для довільного виконання shell-команд або процесів.',
    'Steam credentials are never persisted by AccountManager.': 'AccountManager ніколи не зберігає облікові дані Steam.',
    'Destructive actions require an explicit confirmation dialog.': 'Небезпечні дії потребують явного підтвердження в діалозі.',

    'Working set': 'Робочий набір пам’яті',
    'Disk free': 'Вільно на диску',
    'CPU threads': 'Потоки CPU',
    'reported by runtime': 'за даними середовища виконання',
    'Waiting input': 'Очікують введення',
    'interactive bot requests': 'інтерактивні запити ботів',
    'Modules': 'Модулі',
    'Loaded assemblies and expected release versions.': 'Завантажені збірки та очікувані версії релізу.',
    'No module data.': 'Даних про модулі немає.',
    'Read-only process environment.': 'Середовище процесу лише для читання.',
    'OS': 'ОС',
    'Architecture': 'Архітектура',
    'ASF process actions': 'Дії з процесом ASF',
    'Native authenticated ASF endpoints only. No host shell is exposed.': 'Лише штатні автентифіковані endpoints ASF. Доступу до shell хоста немає.',
    'confirmation required': 'потрібне підтвердження',
    'Restart ASF': 'Перезапустити ASF',
    'Exit ASF': 'Завершити ASF',
    'OK': 'OK',
    'VERSION': 'ВЕРСІЯ',
    'MISSING': 'ВІДСУТНІЙ',
    'loaded': 'завантажено',
    'expected': 'очікується',

    'Pinned compatibility': 'Зафіксована сумісність',
    'Control Suite 1.0 is built against a fixed baseline.': 'Control Suite 1.0 збирається для зафіксованої базової версії.',
    'pinned': 'зафіксовано',
    'Control modules': 'Модулі керування',
    'Ownership boundaries': 'Межі відповідальності',
    'Each module has one clear job.': 'Кожен модуль має одну чітку відповідальність.',
    'Managed GamesPlayed, Family availability and Family View journal.': 'Керує GamesPlayed, сімейною доступністю та журналом Family View.',
    'Credential-free defaults and account summary.': 'Значення за замовчуванням без секретів і зведення облікових записів.',
    'Read-only runtime and module health.': 'Стан середовища та модулів лише для читання.',
    'Presentation and orchestration through existing authenticated APIs.': 'Інтерфейс і координація через наявні автентифіковані API.',
    'Native API': 'Штатний API',
    'Use ASF Swagger when you need direct endpoint inspection.': 'Використовуйте ASF Swagger, коли потрібен прямий перегляд endpoints.',
    'Open API docs': 'Відкрити документацію API',
    'Deployment, backups and rollback remain out-of-band through the ADB installer. The browser cannot execute arbitrary host commands.': 'Розгортання, резервні копії та відкат виконуються окремо через ADB-інсталятор. Браузер не може виконувати довільні команди на хості.',

    'Rename account': 'Перейменувати обліковий запис',
    'Account action': 'Дія з обліковим записом',
    'New bot name': 'Нове ім’я бота',
    'Delete account': 'Видалити обліковий запис',
    'Permanent action': 'Незворотна дія',
    'This cannot be undone from the Control UI.': 'Цю дію неможливо скасувати з Control UI.',
    'Delete permanently': 'Видалити назавжди',
    'Bot name, Steam login and Steam password are required': 'Потрібно вказати ім’я бота, логін Steam і пароль Steam',
    'ASF did not return an encrypted Steam password': 'ASF не повернув зашифрований пароль Steam',
    'Input value is required': 'Потрібно ввести значення',
    'No bot selected': 'Бота не вибрано',
    'ASF did not return BotConfig for': 'ASF не повернув BotConfig для',
    'Confirmation text must match': 'Текст підтвердження має точно збігатися з',
    'Authorization expired or was rejected.': 'Авторизація завершилася або була відхилена.',
    'Action failed': 'Не вдалося виконати дію',
    'Input sent': 'Дані надіслано',
    'Input failed': 'Не вдалося надіслати дані',
    'Config enabled': 'Конфігурацію увімкнено',
    'Config disabled': 'Конфігурацію вимкнено',
    'Config update failed': 'Не вдалося оновити конфігурацію',
    'Account renamed': 'Обліковий запис перейменовано',
    'Account deleted': 'Обліковий запис видалено',
    'Account created': 'Обліковий запис створено',
    'Could not create account': 'Не вдалося створити обліковий запис',
    'Defaults saved': 'Значення за замовчуванням збережено',
    'Server-side secret filtering applied.': 'Серверну фільтрацію секретів застосовано.',
    'Defaults not saved': 'Значення за замовчуванням не збережено',
    'PlaytimeGoals saved': 'PlaytimeGoals збережено',
    'PlaytimeGoals not saved': 'PlaytimeGoals не збережено',
    'Configuration written': 'Конфігурацію записано',
    'ASF reload is still settling. Refresh shortly.': 'ASF ще застосовує конфігурацію. Оновіть дані трохи згодом.',
    'Auto-lock updated': 'Автоблокування оновлено',
    'disabled for this tab': 'вимкнено для цієї вкладки',
    'Restart failed': 'Не вдалося перезапустити ASF',
    'Exit failed': 'Не вдалося завершити ASF',
    'Process action': 'Дія з процесом',
    'ASF will restart and the Control UI will temporarily disconnect.': 'ASF буде перезапущено, тому Control UI тимчасово втратить з’єднання.',
    'ASF will exit. An external supervisor is required to start it again.': 'ASF завершить роботу. Для повторного запуску потрібен зовнішній supervisor.',
    'ASF restart requested': 'Запит на перезапуск ASF надіслано',
    'Reconnect after the process is back.': 'Підключіться знову після запуску процесу.',
    'ASF exit requested.': 'Запит на завершення ASF надіслано.',
    'QR code': 'QR-код',
    'Login / password': 'Логін / пароль',
    'Sign-in method': 'Спосіб входу',
    'Internal ASF bot ID': 'Внутрішній ID бота ASF',
    '(optional)': '(необов’язково)',
    'Technical identifier only. The UI shows the Steam persona name as the primary account name.': 'Лише технічний ідентифікатор. В інтерфейсі основною назвою показується ім’я профілю Steam.',
    'Use Steam Mobile QR login or encrypted Steam credentials through native ASF APIs.': 'Використовуйте QR-вхід через Steam Mobile або зашифровані облікові дані через штатний API ASF.',
    'No Steam password is sent or stored for QR login. ASF creates the native Steam QR challenge and this browser renders it locally.': 'Для QR-входу пароль Steam не надсилається і не зберігається. ASF створює штатний QR-запит Steam, а браузер відображає його локально.',
    'AccountManager never receives or persists the Steam password. QR onboarding does not require one.': 'AccountManager ніколи не отримує і не зберігає пароль Steam. Для входу через QR пароль не потрібен.',
    'Scan with Steam Mobile': 'Скануйте через Steam Mobile',
    'Open the Steam app, scan this QR code and confirm the sign-in. The challenge is rendered locally in this browser and automatically refreshes when ASF rotates it.': 'Відкрийте застосунок Steam, відскануйте QR-код і підтвердьте вхід. Запит відображається локально в цьому браузері й автоматично оновлюється, коли ASF змінює його.',
    'QR login': 'Вхід через QR',
    'ASF is waiting for permission to begin its native QR session.': 'ASF очікує дозволу на запуск штатної QR-сесії.',
    'Start QR login': 'Почати вхід через QR',
    'QR login failed': 'Не вдалося виконати вхід через QR',
    'QR will appear here after account creation.': 'QR-код з’явиться тут після створення облікового запису.',
    'Starting Steam QR session…': 'Запуск QR-сесії Steam…',
    'Reconnecting to Steam…': 'Повторне підключення до Steam…',
    'Steam account connected': 'Обліковий запис Steam підключено',
    'QR login could not continue': 'Не вдалося продовжити вхід через QR',
    'QR login could not continue. The bot stopped before QR login completed.': 'Не вдалося продовжити вхід через QR. Бот зупинився до завершення входу.',
    'QR sign-in is active in the Add account card above.': 'Вхід через QR активний у блоці «Додати обліковий запис» вище.',
    'Steam accounts': 'Облікові записи Steam',
    'Rename ASF ID': 'Перейменувати ASF ID',
    'ASF ID:': 'ASF ID:',
    'Sort games': 'Сортування ігор',
    'Managed first': 'Керовані спочатку',
    'Name A → Z': 'Назва A → Я',
    'Name Z → A': 'Назва Я → A',
    'Steam hours high → low': 'Час у Steam: більше → менше',
    'Steam hours low → high': 'Час у Steam: менше → більше',
    'Target high → low': 'Ціль: більше → менше',
    'Target low → high': 'Ціль: менше → більше',
    'AppID ascending': 'AppID за зростанням',
    'AppID descending': 'AppID за спаданням',
    'Own first': 'Власні спочатку',
    'Family first': 'Сімейні спочатку',
    'Open legacy Bots': 'Відкрити стару сторінку Bots',
    'The stock ASF-ui Bots page remains available as a legacy fallback. Normal account management belongs in Control Suite. Deployment, backups and rollback remain out-of-band through the ADB installer. The browser cannot execute arbitrary host commands.': 'Штатна сторінка Bots в ASF-ui залишається резервним старим інтерфейсом. Звичайне керування обліковими записами виконується в Control Suite. Розгортання, резервні копії та відкат виконуються окремо через ADB-інсталятор. Браузер не може виконувати довільні команди на хості.',
    'Local QR renderer failed to load.': 'Не вдалося завантажити локальний QR-рендерер.',
    'Refreshed': 'Оновлено',
    'Refresh failed': 'Не вдалося оновити',
    'Try again': 'Спробувати ще раз',
    'Session expired or password is no longer valid.': 'Сесія завершилася або пароль більше не дійсний.',

    'Language': 'Мова',
    'English': 'English',
    'Ukrainian': 'Українська'
  });

  const STATUS = Object.freeze({
    queued: 'у черзі',
    unknown: 'невідомо',
    'family-not-shareable': 'сімейний доступ заборонено',
    'family-copy-busy': 'сімейна копія зайнята',
    'family-availability-unknown': 'доступність сімейної копії невідома',
    'parental-blocked': 'заблоковано Family View',
    'asf-farming': 'ASF вибиває картки',
    'asf-paused': 'фармер ASF призупинений',
    'free-license-pending': 'отримання безкоштовної ліцензії',
    'free-license-claim-failed': 'не вдалося отримати ліцензію'
  });

  function safeStorageGet() {
    try {
      const raw = localStorage.getItem(ASF_LOCALE_KEY);
      if (!raw) return null;
      try { return JSON.parse(raw); } catch (_) { return raw; }
    } catch (_) { return null; }
  }

  function safeStorageSet(locale) {
    try { localStorage.setItem(ASF_LOCALE_KEY, JSON.stringify(locale)); } catch (_) { /* unavailable storage */ }
  }

  function requestedLocale() {
    const stored = safeStorageGet();
    if (typeof stored === 'string' && stored) return stored;
    return navigator.language || DEFAULT_LOCALE;
  }

  function normalize(locale) {
    const value = String(locale || '').toLowerCase();
    return value === 'uk' || value.startsWith('uk-') ? 'uk-UA' : DEFAULT_LOCALE;
  }

  let requested = requestedLocale();
  let locale = normalize(requested);

  function exact(source) {
    return locale === 'uk-UA' ? (UK[source] ?? source) : source;
  }

  function dynamic(source) {
    if (locale !== 'uk-UA') return source;
    if (Object.prototype.hasOwnProperty.call(UK, source)) return UK[source];

    let m;
    if ((m = source.match(/^(\d+)\/(\d+) connected(?: · (\d+) waiting input)?$/))) { const n=Number(m[3]||0); return `${m[1]}/${m[2]} підключено${m[3] ? ` · ${m[3]} ${n===1?'очікує':'очікують'} введення` : ''}`; }
    if ((m = source.match(/^Locked after (\d+) minute\(s\) of inactivity\.$/))) return `Заблоковано після ${m[1]} хв бездіяльності.`;
    if ((m = source.match(/^(\d+) connected$/))) return `${m[1]} підключено`;
    if ((m = source.match(/^(\d+)% of accounts$/))) return `${m[1]}% облікових записів`;
    if ((m = source.match(/^(\d+) accounts? waiting for interactive input\. Open Accounts to continue login\.$/))) { const n=Number(m[1]); return `${m[1]} ${n===1?'обліковий запис очікує':'облікових записів очікують'} інтерактивного введення. Відкрийте «Облікові записи», щоб продовжити вхід.`; }
    if ((m = source.match(/^(\d+) ASF bots? registered\.$/))) return `Зареєстровано ботів ASF: ${m[1]}.`;
    if ((m = source.match(/^(\d+) Steam accounts? managed by ASF\.$/))) return `ASF керує обліковими записами Steam: ${m[1]}.`;
    if ((m = source.match(/^ASF is waiting for interactive input type (\d+)\.$/))) return `ASF очікує інтерактивне введення типу ${m[1]}.`;
    if ((m = source.match(/^config (enabled|disabled)$/))) return `конфігурація ${m[1] === 'enabled' ? 'увімкнена' : 'вимкнена'}`;
    if ((m = source.match(/^AppID (\d+) · ([^·]+?)(?: · queue #(\d+))?$/))) return `AppID ${m[1]} · ${STATUS[m[2].trim()] || exact(m[2].trim())}${m[3] ? ` · черга №${m[3]}` : ''}`;
    if ((m = source.match(/^· ([a-z0-9-]+)(?: · queue #(\d+))?$/i))) return `· ${STATUS[m[1]] || exact(m[1])}${m[2] ? ` · черга №${m[2]}` : ''}`;
    if ((m = source.match(/^(\d+(?:\.\d+)?)h left$/))) return `залишилося ${m[1]} год`;
    if ((m = source.match(/^(\d+(?:\.\d+)?)h effective$/))) return `${m[1]} год враховано`;
    if ((m = source.match(/^(\d+(?:\.\d+)?)h Steam$/))) return `${m[1]} год у Steam`;
    if ((m = source.match(/^∞ unlimited$/))) return '∞ безліміт';
    if ((m = source.match(/^(\d+) managed$/))) return `${m[1]} під керуванням`;
    if ((m = source.match(/^(\d+) own · (\d+) family$/))) return `${m[1]} власних · ${m[2]} сімейних`;
    if ((m = source.match(/^base (unset|allow|deny) · custom (unset|allow|deny)$/))) {
      const value = (x) => ({unset:'не задано',allow:'дозволено',deny:'заборонено'}[x]);
      return `базове: ${value(m[1])} · власне: ${value(m[2])}`;
    }
    if ((m = source.match(/^loaded (.+) · expected (.+)$/))) return `завантажено ${m[1]} · очікується ${m[2]}`;
    if ((m = source.match(/^(\d+)% of (.+)$/))) return `${m[1]}% від ${m[2]}`;
    if ((m = source.match(/^(\d+) min$/))) return `${m[1]} хв`;
    if ((m = source.match(/^(\d+) minute\(s\)$/))) return `${m[1]} хв`;
    if ((m = source.match(/^(\d+)s$/))) return `${m[1]} с`;
    if ((m = source.match(/^(\d+)m$/))) return `${m[1]} хв`;
    if ((m = source.match(/^(\d+)h (\d+)m$/))) return `${m[1]} год ${m[2]} хв`;
    if ((m = source.match(/^(\d+)d (\d+)h$/))) return `${m[1]} д ${m[2]} год`;
    if ((m = source.match(/^managed (.+)$/))) return `керована пам’ять ${m[1]}`;
    if ((m = source.match(/^(.+) was written with AES-encrypted credentials\.$/))) return `${m[1]} записано з обліковими даними, зашифрованими AES.`;
    if ((m = source.match(/^(.+) is connected\. You can add another account when ready\.$/))) return `${m[1]} підключено. За потреби можна додати ще один обліковий запис.`;
    if ((m = source.match(/^QR login could not continue\. ASF is waiting for input type (\d+)\.$/))) return `Не вдалося продовжити вхід через QR. ASF очікує введення типу ${m[1]}.`;
    if ((m = source.match(/^(.+) · type (\d+)$/))) return `${m[1]} · тип ${m[2]}`;
    if ((m = source.match(/^(.+) reloaded and verified\.$/))) return `${m[1]} перезавантажено та перевірено.`;
    if ((m = source.match(/^Target hours for (.+)$/))) return `Цільові години для ${m[1]}`;
    if ((m = source.match(/^Could not load (.+)$/))) return `Не вдалося завантажити «${exact(m[1])}»`;
    if ((m = source.match(/^Confirmation text must match (.+)\.$/))) return `Текст підтвердження має точно збігатися з ${m[1]}.`;
    if ((m = source.match(/^ASF did not return BotConfig for (.+)$/))) return `ASF не повернув BotConfig для ${m[1]}`;
    if ((m = source.match(/^(Start|Stop|Pause|Resume) requested$/))) {
      const action = {Start:'Запуск',Stop:'Зупинку',Pause:'Призупинення',Resume:'Відновлення'}[m[1]];
      return `${action} запитано`;
    }
    if ((m = source.match(/^Rename (.+)\. ASF will rename the related bot files as well\.$/))) return `Перейменування ${m[1]}. ASF також перейменує пов’язані файли бота.`;
    if ((m = source.match(/^This deletes (.+) and all related ASF files\.$/))) return `Буде видалено ${m[1]} і всі пов’язані файли ASF.`;
    return source;
  }

  function translateText(text) {
    const value = String(text ?? '');
    const leading = value.match(/^\s*/)?.[0] || '';
    const trailing = value.match(/\s*$/)?.[0] || '';
    const body = value.slice(leading.length, value.length - trailing.length);
    if (!body) return value;
    return `${leading}${dynamic(body)}${trailing}`;
  }

  function shouldSkip(node) {
    const parent = node.parentElement;
    if (!parent) return false;
    return ['SCRIPT','STYLE','TEXTAREA','CODE','PRE'].includes(parent.tagName);
  }

  function apply(root = document) {
    locale = normalize(requested);
    document.documentElement.lang = locale === 'uk-UA' ? 'uk' : 'en';

    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    for (const node of nodes) {
      if (shouldSkip(node)) continue;
      const translated = translateText(node.nodeValue);
      if (translated !== node.nodeValue) node.nodeValue = translated;
    }

    const elements = [];
    if (root.nodeType === Node.ELEMENT_NODE && root.matches?.('[aria-label],[placeholder],[title]')) elements.push(root);
    if (root.querySelectorAll) elements.push(...root.querySelectorAll('[aria-label],[placeholder],[title]'));
    for (const el of elements) {
      for (const attr of ['aria-label','placeholder','title']) {
        if (!el.hasAttribute(attr)) continue;
        const current = el.getAttribute(attr);
        const translated = translateText(current);
        if (translated !== current) el.setAttribute(attr, translated);
      }
    }
    syncSelectors();
  }

  function selectorOptions(select) {
    const effectiveRequested = normalize(requested);
    const rows = [
      ['en-US', 'English'],
      ['uk-UA', 'Українська']
    ];
    const markup = rows.map(([value,label]) => `<option value="${value.replaceAll('&','&amp;').replaceAll('\"','&quot;')}">${label}</option>`).join('');
    const signature = `${effectiveRequested}|${markup}`;
    if (select.dataset.i18nSignature !== signature) {
      select.innerHTML = markup;
      select.dataset.i18nSignature = signature;
    }
    const nextValue = rows.some(([value]) => value === effectiveRequested) ? effectiveRequested : locale;
    if (select.value !== nextValue) select.value = nextValue;
    const label = exact('Language');
    if (select.getAttribute('aria-label') !== label) select.setAttribute('aria-label', label);
  }

  function syncSelectors() {
    for (const id of ['localeSelect','authLocaleSelect']) {
      const select = document.getElementById(id);
      if (!select) continue;
      if (select.dataset.i18nWired !== '1') {
        select.dataset.i18nWired = '1';
        select.addEventListener('change', () => setLocale(select.value));
      }
      selectorOptions(select);
    }
  }

  function setLocale(next) {
    requested = String(next || DEFAULT_LOCALE);
    locale = normalize(requested);
    safeStorageSet(requested);
    if (location.protocol === 'http:' || location.protocol === 'https:') {
      location.reload();
      return;
    }
    apply(document);
    document.dispatchEvent(new CustomEvent('control:locale-change', { detail:{ requested, locale } }));
  }

  window.addEventListener('storage', (event) => {
    if (event.key !== ASF_LOCALE_KEY) return;
    requested = requestedLocale();
    locale = normalize(requested);
    if (location.protocol === 'http:' || location.protocol === 'https:') location.reload();
    else apply(document);
  });

  const observer = new MutationObserver((mutations) => {
    if (locale !== 'uk-UA') return;
    for (const mutation of mutations) {
      if (mutation.type === 'characterData') {
        const node = mutation.target;
        if (!shouldSkip(node)) {
          const translated = translateText(node.nodeValue);
          if (translated !== node.nodeValue) node.nodeValue = translated;
        }
        continue;
      }
      if (mutation.type === 'attributes') {
        const el = mutation.target;
        const attr = mutation.attributeName;
        if (attr && ['aria-label','placeholder','title'].includes(attr)) {
          const current = el.getAttribute(attr);
          const translated = translateText(current);
          if (translated !== current) el.setAttribute(attr, translated);
        }
        continue;
      }
      for (const node of mutation.addedNodes) {
        if (node.nodeType === Node.TEXT_NODE) {
          if (!shouldSkip(node)) node.nodeValue = translateText(node.nodeValue);
        } else if (node.nodeType === Node.ELEMENT_NODE) apply(node);
      }
    }
  });

  window.ControlI18n = Object.freeze({
    ASF_LOCALE_KEY,
    SUPPORTED,
    get locale() { return locale; },
    get requestedLocale() { return requested; },
    t: dynamic,
    status: (value) => locale === 'uk-UA' ? (STATUS[String(value)] || dynamic(String(value))) : String(value),
    setLocale,
    apply
  });

  const init = () => {
    apply(document);
    observer.observe(document.body, { childList:true, characterData:true, attributes:true, attributeFilter:['aria-label','placeholder','title'], subtree:true });
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once:true });
  else init();
})();
