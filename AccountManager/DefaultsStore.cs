using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading;
using System.Threading.Tasks;
using ArchiSteamFarm;
using ArchiSteamFarm.Helpers.Json;

namespace AccountManager;

internal sealed class DefaultsStore {
    internal const int MaxPayloadChars = 64 * 1024;

    private static readonly HashSet<string> ForbiddenKeysSet = new(StringComparer.OrdinalIgnoreCase) {
        "SteamLogin", "SteamPassword", "SteamParentalCode", "SteamTradeToken", "PasswordFormat",
        "WebProxyPassword", "IPCPassword", "CryptKey", "AccessToken", "RefreshToken"
    };

    private static readonly string[] SensitiveMarkers = {
        "password", "passwd", "token", "secret", "credential", "apikey", "privatekey",
        "accesskey", "clientsecret", "authorization", "authkey", "cryptkey"
    };

    private static readonly SemaphoreSlim Sync = new(1, 1);
    private readonly string path = Path.Combine(Directory.GetCurrentDirectory(), SharedInfo.ConfigDirectory, "AccountManager.defaults.json");

    internal async Task<JsonObject> Read() {
        await Sync.WaitAsync().ConfigureAwait(false);
        try {
            if (!File.Exists(path)) return new JsonObject();
            string json = await File.ReadAllTextAsync(path).ConfigureAwait(false);
            if (string.IsNullOrWhiteSpace(json) || json.Length > MaxPayloadChars) return new JsonObject();
            JsonNode? node = JsonNode.Parse(json);
            if (node is not JsonObject obj) return new JsonObject();
            StripSecrets(obj);
            return Clone(obj);
        } catch { return new JsonObject(); }
        finally { Sync.Release(); }
    }

    internal async Task<JsonObject?> Write(JsonElement input) {
        if (input.ValueKind != JsonValueKind.Object) return null;
        string raw = input.GetRawText();
        if (raw.Length > MaxPayloadChars) return null;
        JsonNode? parsed = JsonNode.Parse(raw);
        if (parsed is not JsonObject obj) return null;
        StripSecrets(obj);
        await Sync.WaitAsync().ConfigureAwait(false);
        try {
            string? directory = System.IO.Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(directory)) Directory.CreateDirectory(directory);
            await File.WriteAllTextAsync(path, obj.ToJsonText(true)).ConfigureAwait(false);
            return Clone(obj);
        } finally { Sync.Release(); }
    }

    internal static IReadOnlyCollection<string> ForbiddenKeys => ForbiddenKeysSet.OrderBy(static key => key, StringComparer.OrdinalIgnoreCase).ToArray();
    internal static IReadOnlyCollection<string> SensitiveKeyMarkers => SensitiveMarkers.ToArray();

    private static JsonObject Clone(JsonObject source) => JsonNode.Parse(source.ToJsonText()) as JsonObject ?? new JsonObject();

    private static bool IsSensitiveKey(string key) {
        if (ForbiddenKeysSet.Contains(key)) return true;
        string normalized = new string(key.Where(static character => char.IsLetterOrDigit(character)).ToArray());
        return SensitiveMarkers.Any(marker => normalized.Contains(marker, StringComparison.OrdinalIgnoreCase));
    }

    private static void StripSecrets(JsonNode? node) {
        if (node is JsonObject obj) {
            string[] keys = obj.Select(static pair => pair.Key).ToArray();
            foreach (string key in keys) {
                if (IsSensitiveKey(key)) { obj.Remove(key); continue; }
                StripSecrets(obj[key]);
            }
            return;
        }
        if (node is JsonArray array) foreach (JsonNode? item in array) StripSecrets(item);
    }
}
