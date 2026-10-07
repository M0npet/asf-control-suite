#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SUITE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# shellcheck disable=SC1091
. "$SCRIPT_DIR/pins.sh"

load_release_pins "$SUITE_ROOT/release/pins.env"

ASF_ROOT="${1:-$(pwd)}"
SDK="${CONTROL_DOTNET_SDK:-$DOTNET_SDK_VERSION}"

cd "$ASF_ROOT"

[[ "$(git rev-parse HEAD)" == "$ASF_COMMIT" ]] || {
    echo "wrong ASF HEAD" >&2
    exit 2
}

[[ "$(git -C ASF-ui rev-parse HEAD)" == "$ASF_UI_COMMIT" ]] || {
    echo "wrong ASF-ui HEAD" >&2
    exit 3
}

command -v dotnet >/dev/null || {
    echo "dotnet not found" >&2
    exit 4
}

[[ "$(dotnet --version)" == "$SDK" ]] || {
    echo "expected SDK $SDK, got $(dotnet --version)" >&2
    exit 5
}

for project in \
    PlaytimeGoals \
    AccountManager \
    ControlCenter \
    ControlWeb
do
    [[ -f "$project/$project.csproj" ]] || {
        echo "missing project: $project" >&2
        exit 6
    }
done

grep -Fq \
    "<Version>$PLAYTIMEGOALS_VERSION</Version>" \
    PlaytimeGoals/PlaytimeGoals.csproj || {
        echo "unexpected PlaytimeGoals version" >&2
        exit 7
    }

for project in \
    AccountManager \
    ControlCenter \
    ControlWeb
do
    grep -Fq \
        "<Version>$CONTROL_MODULE_VERSION</Version>" \
        "$project/$project.csproj" || {
            echo "unexpected $project version" >&2
            exit 8
        }
done

git diff --check

dotnet restore ArchiSteamFarm/ArchiSteamFarm.csproj

for project in \
    PlaytimeGoals \
    AccountManager \
    ControlCenter \
    ControlWeb
do
    dotnet restore "$project/$project.csproj"
done

dotnet build \
    ArchiSteamFarm/ArchiSteamFarm.csproj \
    -c Release \
    --no-restore \
    -p:ContinuousIntegrationBuild=true \
    -p:UseAppHost=false

ASF_RUNTIME_DIR="out/control-suite-linux-arm64"
ASF_RUNTIME="$ASF_RUNTIME_DIR/ArchiSteamFarm"

rm -rf "$ASF_RUNTIME_DIR"

dotnet publish \
    ArchiSteamFarm/ArchiSteamFarm.csproj \
    -c Release \
    -o "$ASF_RUNTIME_DIR" \
    -p:ASFVariant=linux-arm64 \
    -p:ContinuousIntegrationBuild=true \
    -p:PublishSingleFile=true \
    -p:PublishTrimmed=true \
    -r linux-arm64 \
    --self-contained \
    --nologo

[[ -s "$ASF_RUNTIME" && -x "$ASF_RUNTIME" ]] || {
    echo "missing patched linux-arm64 ASF runtime $ASF_RUNTIME" >&2
    exit 9
}

sha256sum "$ASF_RUNTIME"

for project in \
    PlaytimeGoals \
    AccountManager \
    ControlCenter \
    ControlWeb
do
    dotnet build \
        "$project/$project.csproj" \
        -c Release \
        --no-restore \
        --no-dependencies \
        -p:ContinuousIntegrationBuild=true \
        -p:UseAppHost=false \
        -p:TreatWarningsAsErrors=true

    dll="$project/bin/Release/net10.0/$project.dll"

    [[ -s "$dll" ]] || {
        echo "missing output $dll" >&2
        exit 9
    }

    sha256sum "$dll"
done

for asset in \
    index.html \
    i18n.js \
    core.js \
    native.js \
    qrcode.min.js \
    qrcode.LICENSE.txt \
    app.js \
    app.css
do
    [[ -s "ControlWeb/bin/Release/net10.0/www/$asset" ]] || {
        echo "missing ControlWeb asset $asset" >&2
        exit 10
    }
done

echo "ASF CONTROL SUITE v$CONTROL_SUITE_VERSION + PLAYTIMEGOALS BUILD PASSED"
echo "PlaytimeGoals source commit: $PLAYTIMEGOALS_COMMIT"
