$ErrorActionPreference = "Stop"
$srcPath = "C:\Users\blazi\Downloads\NeuroCortex_v3 (1).jsx"
$root = "C:\Users\blazi\Projects\neurocortex\src"
$lines = Get-Content -LiteralPath $srcPath -Encoding UTF8

function L([int]$a, [int]$b) { ($lines[($a-1)..($b-1)] -join "`n") }
function W([string]$rel, [string]$text) {
  $p = Join-Path $root $rel
  $d = Split-Path $p -Parent
  if (!(Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
  [IO.File]::WriteAllText($p, $text.TrimEnd() + "`n")
}

# ── constants ──
W "constants\tokens.js" (L 32 53 -replace '^const T','export const T')
W "constants\styles.js" ("import { T } from './tokens.js';`n`n" + (L 55 76 -replace '^const css','export const css'))
W "constants\wordBank.js" ((L 79 80) -replace '^const WORD_BANK','export const WORD_BANK' -replace '^const pickWords','export const pickWords')
W "constants\stroop.js" ((L 82 89) -replace '^const STROOP_COLORS','export const STROOP_COLORS' -replace '^const genStroop','export const genStroop')
W "constants\typingPassages.js" (L 91 97 -replace '^const TYPING_PASSAGES','export const TYPING_PASSAGES')
W "constants\gamification.js" @"
import { T } from './tokens.js';

$( (L 229 267) -replace '^const PET_TYPES','export const PET_TYPES' -replace '^const ACHIEVEMENTS_DEF','export const ACHIEVEMENTS_DEF' -replace '^const BRAIN_REGIONS','export const BRAIN_REGIONS' -replace '^const HOUSE_ITEMS','export const HOUSE_ITEMS' )
"@

# ── utils ──
W "utils\ids.js" (L 270 -replace '^const genID','export const genID')
W "utils\dates.js" @"
$( (L 271 274) -replace '^const dateToday','export const dateToday' -replace '^const today','export const today' )

$( (L 277 285) -replace '^function countdownToMidnight','export function countdownToMidnight' )
"@
W "utils\gamification.js" (L 286 288 -replace '^const calcLevel','export const calcLevel' -replace '^const evolStage','export const evolStage' -replace '^const evolEmoji','export const evolEmoji')
W "utils\burnout.js" (L 1446 1455 -replace '^function calcBurnout','export function calcBurnout')
W "utils\export.js" @"
$( (L 1458 1466) -replace '^function buildXLSX','export function buildXLSX' )
$( (L 1468 1476) -replace '^function safeDownload','export function safeDownload' )
"@
W "utils\useInterval.js" @"
import { useEffect, useRef } from 'react';

$( (L 290 294) -replace '^function useInterval','export function useInterval' )
"@

# ── store ──
W "store\gameData.js" @"
import { PET_TYPES } from '../constants/gamification.js';

$( (L 218 227) -replace '^const initGameData','export const initGameData' )
"@
W "store\index.js" @"
import { dateToday } from '../utils/dates.js';

$(L 99 117)

$( (L 118 213) )

// Backward-compat alias — remove once all DB.xxx call-sites are updated
export const DB = Store;
export default Store;
"@

# ── ui ──
$uiImp = "import { T } from '../../constants/tokens.js';`nimport Btn from './Btn.jsx';`n"
W "components\ui\Btn.jsx" @"
import { T } from '../../constants/tokens.js';

$( (L 2084 2093) -replace '^function Btn','export default function Btn' )
"@
W "components\ui\Card.jsx" @"
import { T } from '../../constants/tokens.js';

$( (L 2080 2082) -replace '^function Card','export default function Card' )
"@
W "components\ui\Page.jsx" @"
import Btn from './Btn.jsx';

$( (L 2068 2078) -replace '^function Page','export default function Page' )
"@
W "components\ui\SectionTitle.jsx" @"
import { T } from '../../constants/tokens.js';

$( (L 2095 2097) -replace '^function SectionTitle','export default function SectionTitle' )
"@
W "components\ui\Label.jsx" @"
import { T } from '../../constants/tokens.js';

$( (L 2099 2101) -replace '^function Label','export default function Label' )
"@
W "components\ui\LockedScreen.jsx" @"
import Page from './Page.jsx';
import Card from './Card.jsx';
import { T } from '../../constants/tokens.js';

$( (L 2103 2113) -replace '^function LockedScreen','export default function LockedScreen' )
"@
W "components\ui\Toast.jsx" @"
import { T } from '../../constants/tokens.js';

$( (L 2115 2122) -replace '^function Toast','export default function Toast' )
"@
W "components\ui\SparkLine.jsx" @"
import { T } from '../../constants/tokens.js';

$( (L 835 862) -replace '^function SparkLine','export default function SparkLine' )
"@

# ── auth ──
W "components\auth\Splash.jsx" @"
import { T } from '../../constants/tokens.js';

$( (L 431 440) -replace '^function Splash','export default function Splash' )
"@
W "components\auth\Welcome.jsx" @"
import { T } from '../../constants/tokens.js';
import Btn from '../ui/Btn.jsx';

$( (L 443 459) -replace '^function Welcome','export default function Welcome' )
"@
W "components\auth\RegisterScreen.jsx" @"
import { useState } from 'react';
import { T } from '../../constants/tokens.js';
import Store from '../../store/index.js';
import { initGameData } from '../../store/gameData.js';
import { PET_TYPES } from '../../constants/gamification.js';
import { genID } from '../../utils/ids.js';
import { dateToday } from '../../utils/dates.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import Label from '../ui/Label.jsx';

$( (L 465 569) -replace '^function RegisterScreen','export default function RegisterScreen' )
"@
W "components\auth\LoginScreen.jsx" @"
import { useState, useMemo } from 'react';
import { T } from '../../constants/tokens.js';
import Store from '../../store/index.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';

$( (L 575 622) -replace '^function LoginScreen','export default function LoginScreen' )
"@

# ── modules ──
W "components\modules\ReactionTest.jsx" @"
import { useState, useRef, useCallback } from 'react';
import { T } from '../../constants/tokens.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import LockedScreen from '../ui/LockedScreen.jsx';

$( (L 869 948) -replace '^function ReactionTest','export default function ReactionTest' )
"@
W "components\modules\TypingTest.jsx" @"
import { useState, useEffect, useRef, useCallback } from 'react';
import { T } from '../../constants/tokens.js';
import { TYPING_PASSAGES } from '../../constants/typingPassages.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import LockedScreen from '../ui/LockedScreen.jsx';

$( (L 951 1043) -replace '^function TypingTest','export default function TypingTest' )
"@
W "components\modules\MemoryTest.jsx" @"
import { useState, useEffect, useRef } from 'react';
import { T } from '../../constants/tokens.js';
import { pickWords } from '../../constants/wordBank.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import LockedScreen from '../ui/LockedScreen.jsx';

$( (L 1046 1129) -replace '^function MemoryTest','export default function MemoryTest' )
"@
W "components\modules\AttentionTest.jsx" @"
import { useState } from 'react';
import { T } from '../../constants/tokens.js';
import { STROOP_COLORS, genStroop } from '../../constants/stroop.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import LockedScreen from '../ui/LockedScreen.jsx';

$( (L 1132 1191) -replace '^function AttentionTest','export default function AttentionTest' )
"@
W "components\modules\DailySurvey.jsx" @"
import { useState, useMemo } from 'react';
import { T } from '../../constants/tokens.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import LockedScreen from '../ui/LockedScreen.jsx';

$( (L 1194 1243) -replace '^function DailySurvey','export default function DailySurvey' )
"@
W "components\modules\NasaTLX.jsx" @"
import { useState } from 'react';
import { T } from '../../constants/tokens.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';

$( (L 1246 1287) -replace '^function NasaTLX','export default function NasaTLX' )
"@

# ── dashboard ──
W "components\dashboard\MiniBar.jsx" @"
import { T } from '../../constants/tokens.js';

$( (L 728 740) -replace '^function MiniBar','export default function MiniBar' )
"@
W "components\dashboard\PetBanner.jsx" @"
import { T } from '../../constants/tokens.js';
import { PET_TYPES } from '../../constants/gamification.js';
import { evolEmoji } from '../../utils/gamification.js';
import MiniBar from './MiniBar.jsx';

$( (L 704 726) -replace '^function PetBanner','export default function PetBanner' )
"@
W "components\dashboard\TodayTab.jsx" @"
import { T } from '../../constants/tokens.js';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';

$( (L 742 807) -replace '^function TodayTab','export default function TodayTab' )
"@
W "components\dashboard\ProgressTab.jsx" @"
import { T } from '../../constants/tokens.js';
import Card from '../ui/Card.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import SparkLine from '../ui/SparkLine.jsx';

$( (L 809 832) -replace '^function ProgressTab','export default function ProgressTab' )
"@
W "components\dashboard\Dashboard.jsx" @"
import { useState } from 'react';
import { T } from '../../constants/tokens.js';
import Btn from '../ui/Btn.jsx';
import PetBanner from './PetBanner.jsx';
import TodayTab from './TodayTab.jsx';
import ProgressTab from './ProgressTab.jsx';

$( (L 625 702) -replace '^function Dashboard','export default function Dashboard' )
"@

# ── gamification ──
W "components\gamification\PetScreen.jsx" @"
import { useState } from 'react';
import { T } from '../../constants/tokens.js';
import { PET_TYPES, HOUSE_ITEMS } from '../../constants/gamification.js';
import { evolEmoji } from '../../utils/gamification.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';

$( (L 1293 1370) -replace '^function PetScreen','export default function PetScreen' )
"@
W "components\gamification\AchievementsScreen.jsx" @"
import { T } from '../../constants/tokens.js';
import { ACHIEVEMENTS_DEF } from '../../constants/gamification.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';

$( (L 1372 1391) -replace '^function AchievementsScreen','export default function AchievementsScreen' )
"@
W "components\gamification\NeuroVerse.jsx" @"
import { T } from '../../constants/tokens.js';
import { BRAIN_REGIONS } from '../../constants/gamification.js';
import Page from '../ui/Page.jsx';
import Card from '../ui/Card.jsx';

$( (L 1393 1437) -replace '^function NeuroVerse','export default function NeuroVerse' )
"@

# ── research ──
W "components\research\ResearchOverviewTab.jsx" @"
import { T } from '../../constants/tokens.js';
import Card from '../ui/Card.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import SparkLine from '../ui/SparkLine.jsx';

$( (L 1792 1843) -replace '^function ResearchOverviewTab','export default function ResearchOverviewTab' )
"@
W "components\research\ParticipantsTab.jsx" @"
import { T } from '../../constants/tokens.js';
import { calcBurnout } from '../../utils/burnout.js';
import Card from '../ui/Card.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';

$( (L 1850 1934) -replace '^function ParticipantsTab','export default function ParticipantsTab' )
"@
W "components\research\MLTab.jsx" @"
import { T } from '../../constants/tokens.js';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';

$( (L 1940 2003) -replace '^function MLTab','export default function MLTab' )
"@
W "components\research\ExportTab.jsx" @"
import { T } from '../../constants/tokens.js';
import Card from '../ui/Card.jsx';
import Btn from '../ui/Btn.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';

$( (L 2010 2065) -replace '^function ExportTab','export default function ExportTab' )
"@
W "components\research\ResearcherDashboard.jsx" @"
import { useState, useEffect, useMemo } from 'react';
import { T } from '../../constants/tokens.js';
import Store from '../../store/index.js';
import { dateToday } from '../../utils/dates.js';
import { calcBurnout } from '../../utils/burnout.js';
import { buildXLSX, safeDownload } from '../../utils/export.js';
import Btn from '../ui/Btn.jsx';
import Card from '../ui/Card.jsx';
import ResearchOverviewTab from './ResearchOverviewTab.jsx';
import ParticipantsTab from './ParticipantsTab.jsx';
import MLTab from './MLTab.jsx';
import ExportTab from './ExportTab.jsx';

$( (L 1478 1786) -replace '^function ResearcherDashboard','export default function ResearcherDashboard' )
"@

# ── App ──
W "App.jsx" @"
import { useState, useEffect, useCallback, useMemo } from 'react';
import { T } from './constants/tokens.js';
import { css } from './constants/styles.js';
import Store from './store/index.js';
import { initGameData } from './store/gameData.js';
import { ACHIEVEMENTS_DEF, BRAIN_REGIONS } from './constants/gamification.js';
import { dateToday, today, countdownToMidnight } from './utils/dates.js';
import { calcLevel, evolStage } from './utils/gamification.js';
import Splash from './components/auth/Splash.jsx';
import Welcome from './components/auth/Welcome.jsx';
import RegisterScreen from './components/auth/RegisterScreen.jsx';
import LoginScreen from './components/auth/LoginScreen.jsx';
import Dashboard from './components/dashboard/Dashboard.jsx';
import ReactionTest from './components/modules/ReactionTest.jsx';
import TypingTest from './components/modules/TypingTest.jsx';
import MemoryTest from './components/modules/MemoryTest.jsx';
import AttentionTest from './components/modules/AttentionTest.jsx';
import DailySurvey from './components/modules/DailySurvey.jsx';
import NasaTLX from './components/modules/NasaTLX.jsx';
import PetScreen from './components/gamification/PetScreen.jsx';
import AchievementsScreen from './components/gamification/AchievementsScreen.jsx';
import NeuroVerse from './components/gamification/NeuroVerse.jsx';
import ResearcherDashboard from './components/research/ResearcherDashboard.jsx';
import Toast from './components/ui/Toast.jsx';

$( (L 299 428) )
"@

W "main.jsx" @"
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
"@

# Copy legacy source
New-Item -ItemType Directory -Path "C:\Users\blazi\Projects\neurocortex\legacy" -Force | Out-Null
Copy-Item -LiteralPath $srcPath -Destination "C:\Users\blazi\Projects\neurocortex\legacy\NeuroCortex_v3.jsx" -Force

Write-Host "Split complete. Files written to $root"
