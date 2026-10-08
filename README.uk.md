<div align="center">

# ASF Control Suite

### Безпечний модульний центр керування для ArchiSteamFarm

**main: v1.1.0 candidate · stable: v1.0.0 · ASF 6.3.10.3 · .NET 10.0.400**

[English](README.md) · [Українська](README.uk.md) · [Deutsch](README.de.md)

</div>

---

## Про проєкт

ASF Control Suite додає до ArchiSteamFarm єдиний інтерфейс із `/` як стандартною точкою входу та `/Control/` як канонічним внутрішнім шляхом, при цьому автентифікація, життєвий цикл ботів і конфігурація залишаються під контролем самого ASF.

Проєкт побудований як набір невеликих нативних ASF-плагінів без другого демона та без довільного shell-інтерфейсу.

| Модуль | Призначення |
| --- | --- |
| **AccountManager** | Огляд кількох акаунтів, Steam-ім'я й аватар, керування ботами та QR/password onboarding |
| **ControlCenter** | Стан системи, модулів і дані сумісності |
| **ControlWeb** | Єдиний локальний вебінтерфейс; `/` — стандартна точка входу, `/Control/` — канонічний внутрішній шлях |
| **PlaytimeGoals** | Цілі ігрового часу, черги, FREE-ліцензії та відновлення Family View |

---

## Версії

Єдине канонічне джерело версій і revision-пінів — [`release/pins.env`](release/pins.env).

| Компонент | Версія / revision |
| --- | --- |
| ASF Control Suite | **1.1.0 candidate** |
| Control-модулі | **1.1.0.0** |
| ArchiSteamFarm | **6.3.10.3** |
| ASF commit | `27bd1d5dbdc8c4897eaaed0e3246d10ffe18b0ad` |
| ASF-ui commit | `2b36125533f41e624b2fdcdec44f37ad60c7daaa` |
| PlaytimeGoals | **0.5.3.0** |
| PlaytimeGoals commit | `f7c1bfe74c9203fe089830f1646a3d2ba54150de` |
| .NET SDK | **10.0.400** |

---

## Основні можливості

### Керування акаунтами

- Steam-імена та аватари
- дії ASF окремо для кожного акаунта
- нативний Steam QR login
- додавання акаунтів через пароль із використанням ASF API
- без окремого сховища облікових даних

### PlaytimeGoals

- обмежені та необмежені цілі часу
- окремі черги ігор для акаунтів
- підтримка Steam Family
- автоматична робота з FREE-ліцензіями
- відновлення Family View
- секундна точність локальних дедлайнів для обмежених цілей у PlaytimeGoals 0.5.3

### ControlWeb

- `/` відкриває Control Suite за замовчуванням; `/Control/` залишається канонічним внутрішнім шляхом
- desktop і mobile layout
- англійська та українська локалізація з інтеграцією ASF-ui locale
- локальні JS, CSS і QR assets
- без довільного shell/process API

---

## Модель безпеки

Авторитетним механізмом автентифікації залишається ASF IPC.

IPC password існує лише в **пам'яті сторінки** поточного автентифікованого документа. Він не зберігається в browser storage та зникає після refresh, lock, logout, помилки автентифікації або закриття сторінки.

Steam-паролі шифруються через ASF до запису BotConfig.

ControlWeb не надає API для довільного запуску shell-команд або процесів. QR-коди та вебресурси генеруються і зберігаються локально.

Політика безпеки: [`SECURITY.md`](SECURITY.md).

---

## Нативні ASF-пакети

Канонічна release-збірка створює:

    ASF-Control-Suite-v1.1.0.zip
    AccountManager-v1.1.0.zip
    ControlCenter-v1.1.0.zip
    ControlWeb-v1.1.0.zip
    PlaytimeGoals-v0.5.2.zip
    CONTROL-SUITE-METADATA.json
    SHA256SUMS

ZIP-файли вже мають нативну структуру ASF plugins.

Для встановлення повного bundle:

1. Зупиніть ASF.
2. Розпакуйте `ASF-Control-Suite-v1.1.0.zip` прямо в корінь `<ASF>/`.
3. Запустіть ASF.
4. Відкрийте `/` і перевірте Control Suite та `/Control/`.

Окремі plugin ZIP-файли розпаковуються в `<ASF>/plugins/`.

Наведені вище імена пакетів відповідають поточному кандидату `main` v1.1.0. Стабільний реліз залишається [v1.0.0](https://github.com/M0npet/asf-control-suite/releases/tag/v1.0.0) до проходження нового live acceptance.

---

## Відтворювана release-збірка

Release pipeline працює за принципом fail-closed:

    release/pins.env
          ↓
    точні source revisions
          ↓
    точний .NET SDK 10.0.400
          ↓
    build із warnings-as-errors
          ↓
    єдиний canonical staging tree
          ↓
    детерміновані ZIP-файли
          ↓
    metadata + SHA256SUMS
          ↓
    provenance verification

Verifier порівнює байти exact build з bundle та individual ZIP.

Просте повторне обчислення `SHA256SUMS` після зміни артефакту не дозволяє обійти provenance-перевірку.

---

## Збірка

За наявності локальних Git-репозиторіїв ASF і PlaytimeGoals з потрібними revision:

    bash scripts/build/make-release.sh \
      /path/to/ArchiSteamFarm \
      /path/to/PlaytimeGoals

Повна інструкція: [`docs/installation/manual.md`](docs/installation/manual.md).

---

## Тести

Повний локальний набір тестів:

    bash tests/run-all.sh

Він перевіряє, зокрема:

- цілісність release pins
- generated BuildInfo
- RAM-only IPC authentication
- supply chain .NET SDK
- deterministic ZIP packaging
- byte identity build/package
- release provenance
- логіку ControlWeb
- browser integration
- transactional phone deployment і rollback fixtures

---

## Документація

- [Встановлення](docs/installation/manual.md)
- [Архітектура](docs/architecture/README.md)
- [Розробка](docs/development/README.md)
- [Матриця функцій](docs/FUNCTION_MATRIX.md)
- [Політика безпеки](SECURITY.md)
- [Участь у розробці](CONTRIBUTING.md)

---

<div align="center">

**ASF Control Suite · main v1.1.0 candidate · stable v1.0.0**

ASF-native API, відтворювані збірки та чіткі межі безпеки.

</div>
