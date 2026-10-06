using System;
using System.Linq;
using System.Reflection;
using ArchiSteamFarm.Core;
using ArchiSteamFarm.Steam;
using Microsoft.AspNetCore.Mvc;

namespace ControlCenter;

[ApiController]
[Route("Api/ControlCenter")]
public sealed class ControlCenterController : ControllerBase {
    private static readonly string[] Capabilities = {
        "health", "runtime-summary", "bot-summary", "module-summary",
        "native-asf-restart-via-web", "native-asf-exit-via-web"
    };

    private static object Module(string assemblyName, string expectedVersion) {
        Assembly? assembly = AppDomain.CurrentDomain.GetAssemblies()
            .FirstOrDefault(item => string.Equals(item.GetName().Name, assemblyName, StringComparison.OrdinalIgnoreCase));

        return new {
            Name = assemblyName,
            Loaded = assembly != null,
            Version = assembly?.GetName().Version?.ToString() ?? string.Empty,
            ExpectedVersion = expectedVersion
        };
    }

    private static object BuildStatusResult() {
        Bot[] bots = Bot.BotsReadOnly?.Values.ToArray() ?? Array.Empty<Bot>();
        DateTime now = DateTime.UtcNow;
        Version version = typeof(ControlCenterPlugin).Assembly.GetName().Version ?? new Version(ControlCenterPlugin.ControlModuleVersion);
        // Keep ControlCenter independent from optional runtime metadata members. ASF's linux-arm64
        // self-contained runtime is trimmed and can remove otherwise-normal Environment accessors.
        // Host/runtime details are rendered from ASF's own /Api/ASF response in ControlWeb instead.

        return new {
            Healthy = true,
            PluginVersion = version.ToString(),
            ControlSuiteVersion = ControlCenterPlugin.ControlSuiteVersion,
            ControlModuleVersion = ControlCenterPlugin.ControlModuleVersion,
            TargetAsfVersion = ControlCenterPlugin.TargetAsfVersion,
            TargetAsfCommit = ControlCenterPlugin.TargetAsfCommit,
            TargetAsfUiCommit = ControlCenterPlugin.TargetAsfUiCommit,
            TargetPlaytimeGoalsCommit = ControlCenterPlugin.TargetPlaytimeGoalsCommit,
            TargetPlaytimeGoalsVersion = ControlCenterPlugin.TargetPlaytimeGoalsVersion,
            LoadedAtUtc = ControlCenterPlugin.LoadedAtUtc.ToString("O"),
            UptimeSeconds = Math.Max(0, (long) (now - ControlCenterPlugin.LoadedAtUtc).TotalSeconds),
            ManagedBots = bots.Length,
            ConnectedBots = bots.Count(static bot => bot.IsConnectedAndLoggedOn),
            RunningBots = bots.Count(static bot => bot.KeepRunning),
            FarmingBots = bots.Count(static bot => bot.CardsFarmer.NowFarming),
            WaitingForInputBots = bots.Count(static bot => bot.RequiredInput != ASF.EUserInputType.None),
            ManagedMemoryKiB = (long) GC.GetTotalMemory(false) / 1024L,
            // Filesystem telemetry is intentionally not probed in-process. The exact ASF
            // linux-arm64 trimmed runtime can remove otherwise-normal filesystem members before
            // this plugin is JIT-compiled, so even a try/catch cannot make direct calls safe.
            StorageAvailable = false,
            DiskTotalBytes = (long?) null,
            DiskFreeBytes = (long?) null,
            Modules = new[] {
                Module("PlaytimeGoals", ControlCenterPlugin.TargetPlaytimeGoalsVersion),
                Module("AccountManager", ControlCenterPlugin.ControlModuleVersion),
                Module("ControlCenter", ControlCenterPlugin.ControlModuleVersion),
                Module("ControlWeb", ControlCenterPlugin.ControlModuleVersion)
            },
            Capabilities,
            Safety = new {
                ShellExecution = false,
                ArbitraryHostCommands = false,
                NativeAsfMutationsOnly = true,
                DeploymentIsOutOfBand = true
            }
        };
    }

    [HttpGet("Status")]
    public IActionResult GetStatus() => Ok(new {
        Success = true,
        Message = (string?) null,
        Result = BuildStatusResult()
    });

    // Minimal unauthenticated liveness probe for the local transactional installer. It exposes
    // no runtime data, but deliberately exercises the exact status builder so a trimmed-runtime
    // incompatibility causes installation verification to fail and roll back automatically.
    [HttpGet("/Control/healthz")]
    public IActionResult GetHealth() {
        _ = BuildStatusResult();

        // Keep this on ControllerBase.Ok(object), which ASF itself uses and therefore preserves
        // in its trimmed runtime. Avoid optional MVC helper overloads such as Content(...).
        return Ok(new { Healthy = true, Probe = "control-suite-health" });
    }
}
