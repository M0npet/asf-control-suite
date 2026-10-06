#!/usr/bin/env bash
set -Eeuo pipefail

ASF_ROOT="${1:-$(pwd)}"
SDK="${CONTROL_DOTNET_SDK:-10.0.400}"
ASF_COMMIT="27bd1d5dbdc8c4897eaaed0e3246d10ffe18b0ad"
ASF_UI_COMMIT="2b36125533f41e624b2fdcdec44f37ad60c7daaa"
PTG_COMMIT="fa959d3d4ffd09f7fd30e9ee8599aa5004b67033"

cd "$ASF_ROOT"
[[ "$(git rev-parse HEAD)" == "$ASF_COMMIT" ]] || { echo "wrong ASF HEAD" >&2; exit 2; }
[[ "$(git -C ASF-ui rev-parse HEAD)" == "$ASF_UI_COMMIT" ]] || { echo "wrong ASF-ui HEAD" >&2; exit 3; }
command -v dotnet >/dev/null || { echo "dotnet not found" >&2; exit 4; }
[[ "$(dotnet --version)" == "$SDK" ]] || { echo "expected SDK $SDK, got $(dotnet --version)" >&2; exit 5; }
for p in PlaytimeGoals AccountManager ControlCenter ControlWeb; do
  [[ -f "$p/$p.csproj" ]] || { echo "missing project: $p" >&2; exit 6; }
done
grep -Fq '<Version>0.5.0.0</Version>' PlaytimeGoals/PlaytimeGoals.csproj || { echo "unexpected PlaytimeGoals version" >&2; exit 7; }
for p in AccountManager ControlCenter ControlWeb; do
  grep -Fq '<Version>1.0.0.0</Version>' "$p/$p.csproj" || { echo "unexpected $p version" >&2; exit 8; }
done

git diff --check

dotnet restore ArchiSteamFarm/ArchiSteamFarm.csproj
for p in PlaytimeGoals AccountManager ControlCenter ControlWeb; do
  dotnet restore "$p/$p.csproj"
done

dotnet build ArchiSteamFarm/ArchiSteamFarm.csproj -c Release --no-restore \
  -p:ContinuousIntegrationBuild=true -p:UseAppHost=false

for p in PlaytimeGoals AccountManager ControlCenter ControlWeb; do
  dotnet build "$p/$p.csproj" -c Release --no-restore --no-dependencies \
    -p:ContinuousIntegrationBuild=true -p:UseAppHost=false -p:TreatWarningsAsErrors=true
  dll="$p/bin/Release/net10.0/$p.dll"
  [[ -s "$dll" ]] || { echo "missing output $dll" >&2; exit 9; }
  sha256sum "$dll"
done

for f in index.html i18n.js core.js qrcode.min.js qrcode.LICENSE.txt app.js app.css; do
  [[ -s "ControlWeb/bin/Release/net10.0/www/$f" ]] || { echo "missing ControlWeb asset $f" >&2; exit 10; }
done

echo "ASF CONTROL SUITE v1.0 + PLAYTIMEGOALS BUILD PASSED"
echo "PlaytimeGoals source commit: $PTG_COMMIT"
