#!/usr/bin/env bash

load_release_pins() {
    local pins_file="${1:-}"
    local line=""
    local key=""
    local value=""

    if [[ -z "$pins_file" || ! -r "$pins_file" ]]; then
        echo "release pins file not readable: $pins_file" >&2
        return 90
    fi

    local -A seen=()

    while IFS= read -r line || [[ -n "$line" ]]; do
        line="${line%$'\r'}"

        [[ -z "$line" ]] && continue
        [[ "$line" == \#* ]] && continue

        if [[ ! "$line" =~ ^([A-Z][A-Z0-9_]*)=([A-Za-z0-9._-]+)$ ]]; then
            echo "invalid release pin syntax" >&2
            return 91
        fi

        key="${BASH_REMATCH[1]}"
        value="${BASH_REMATCH[2]}"

        case "$key" in
            CONTROL_SUITE_VERSION|\
            CONTROL_MODULE_VERSION|\
            ASF_VERSION|\
            ASF_COMMIT|\
            ASF_PATCH_SHA256|\
            ASF_UI_COMMIT|\
            PLAYTIMEGOALS_VERSION|\
            PLAYTIMEGOALS_COMMIT|\
            DOTNET_SDK_VERSION)
                ;;
            *)
                echo "unknown release pin: $key" >&2
                return 92
                ;;
        esac

        if [[ -n "${seen[$key]+x}" ]]; then
            echo "duplicate release pin: $key" >&2
            return 93
        fi

        seen["$key"]=1
        printf -v "$key" '%s' "$value"
    done < "$pins_file"

    local required=""

    for required in \
        CONTROL_SUITE_VERSION \
        CONTROL_MODULE_VERSION \
        ASF_VERSION \
        ASF_COMMIT \
        ASF_PATCH_SHA256 \
        ASF_UI_COMMIT \
        PLAYTIMEGOALS_VERSION \
        PLAYTIMEGOALS_COMMIT \
        DOTNET_SDK_VERSION
    do
        if [[ -z "${seen[$required]+x}" ]]; then
            echo "missing release pin: $required" >&2
            return 94
        fi
    done

    [[ "$CONTROL_SUITE_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
        echo "invalid CONTROL_SUITE_VERSION" >&2
        return 95
    }

    [[ "$CONTROL_MODULE_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
        echo "invalid CONTROL_MODULE_VERSION" >&2
        return 95
    }

    [[ "$ASF_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
        echo "invalid ASF_VERSION" >&2
        return 95
    }

    [[ "$ASF_COMMIT" =~ ^[0-9a-f]{40}$ ]] || {
        echo "invalid ASF_COMMIT" >&2
        return 95
    }

    [[ "$ASF_PATCH_SHA256" =~ ^[0-9a-f]{64}$ ]] || {
        echo "invalid ASF_PATCH_SHA256" >&2
        return 95
    }

    [[ "$ASF_UI_COMMIT" =~ ^[0-9a-f]{40}$ ]] || {
        echo "invalid ASF_UI_COMMIT" >&2
        return 95
    }

    [[ "$PLAYTIMEGOALS_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
        echo "invalid PLAYTIMEGOALS_VERSION" >&2
        return 95
    }

    [[ "$PLAYTIMEGOALS_COMMIT" =~ ^[0-9a-f]{40}$ ]] || {
        echo "invalid PLAYTIMEGOALS_COMMIT" >&2
        return 95
    }

    [[ "$DOTNET_SDK_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
        echo "invalid DOTNET_SDK_VERSION" >&2
        return 95
    }

    return 0
}
