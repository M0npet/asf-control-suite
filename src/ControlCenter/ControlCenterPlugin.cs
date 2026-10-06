using System;
using System.Composition;
using System.Threading.Tasks;
using ArchiSteamFarm.Core;
using ArchiSteamFarm.Plugins.Interfaces;
using JetBrains.Annotations;

namespace ControlCenter;

[Export(typeof(IPlugin))]
[UsedImplicitly]
internal sealed class ControlCenterPlugin : IPlugin {
    internal const string ControlSuiteVersion = BuildInfo.ControlSuiteVersion;
    internal const string ControlModuleVersion = BuildInfo.ControlModuleVersion;
    internal const string TargetAsfVersion = BuildInfo.TargetAsfVersion;
    internal const string TargetAsfCommit = BuildInfo.TargetAsfCommit;
    internal const string TargetAsfPatchSha256 = BuildInfo.TargetAsfPatchSha256;
    internal const string TargetAsfUiCommit = BuildInfo.TargetAsfUiCommit;
    internal const string TargetPlaytimeGoalsVersion = BuildInfo.TargetPlaytimeGoalsVersion;
    internal const string TargetPlaytimeGoalsCommit = BuildInfo.TargetPlaytimeGoalsCommit;
    internal static DateTime LoadedAtUtc { get; } = DateTime.UtcNow;
    public string Name => "ControlCenter";
    public Version Version => typeof(ControlCenterPlugin).Assembly.GetName().Version ?? new Version(ControlModuleVersion);
    public Task OnLoaded() { ASF.ArchiLogger.LogGenericInfo($"ControlCenter {Version} loaded (ASF Control Suite {ControlSuiteVersion})"); return Task.CompletedTask; }
}
