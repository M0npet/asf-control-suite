using System;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using ArchiSteamFarm.Steam;
using Microsoft.AspNetCore.Mvc;

namespace AccountManager;

[ApiController]
[Route("Api/AccountManager")]
public sealed class AccountManagerController : ControllerBase {
    [HttpGet]
    public IActionResult GetAccounts() {
        var bots = Bot.BotsReadOnly;

        var accounts = bots == null
            ? Array.Empty<object>()
            : bots.Values
                .OrderBy(static bot => bot.BotName, StringComparer.OrdinalIgnoreCase)
                .Select(
                    static bot => (object) new {
                        bot.BotName,
                        bot.Nickname,
                        bot.AvatarHash,
                        QrChallengeUrl = bot.QrChallengeURL?.ToString(),
                        SteamId = bot.SSteamID,
                        Enabled = bot.BotConfig.Enabled,
                        bot.KeepRunning,
                        Connected = bot.IsConnectedAndLoggedOn,
                        bot.IsPlayingPossible,
                        Farming = bot.CardsFarmer.NowFarming,
                        FarmerPaused = bot.CardsFarmer.Paused,
                        bot.HasMobileAuthenticator,
                        bot.RequiredInput
                    }
                )
                .ToArray();

        return Ok(
            new {
                Success = true,
                Message = (string?) null,
                Result = new {
                    Count = accounts.Length,
                    Accounts = accounts
                }
            }
        );
    }

    [HttpGet("Defaults")]
    public async Task<IActionResult> GetDefaults() {
        var defaults = await AccountManagerPlugin.Defaults.Read().ConfigureAwait(false);

        return Ok(
            new {
                Success = true,
                Message = (string?) null,
                Result = new {
                    Defaults = defaults,
                    ForbiddenKeys = DefaultsStore.ForbiddenKeys,
                    SensitiveKeyMarkers = DefaultsStore.SensitiveKeyMarkers,
                    MaxPayloadChars = DefaultsStore.MaxPayloadChars
                }
            }
        );
    }

    [HttpPost("Defaults")]
    public async Task<IActionResult> SetDefaults([FromBody] JsonElement defaults) {
        var saved = await AccountManagerPlugin.Defaults.Write(defaults).ConfigureAwait(false);

        if (saved == null) {
            return BadRequest(
                new {
                    Success = false,
                    Message = "Defaults payload must be a JSON object no larger than 64 KiB",
                    Result = (object?) null
                }
            );
        }

        return Ok(
            new {
                Success = true,
                Message = "Defaults saved; credentials and security-controlled fields are never persisted",
                Result = new {
                    Defaults = saved,
                    ForbiddenKeys = DefaultsStore.ForbiddenKeys,
                    SensitiveKeyMarkers = DefaultsStore.SensitiveKeyMarkers,
                    MaxPayloadChars = DefaultsStore.MaxPayloadChars
                }
            }
        );
    }
}
