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
    internal const string TargetAsfVersion = "6.3.10.3";
    internal const string TargetAsfCommit = "27bd1d5dbdc8c4897eaaed0e3246d10ffe18b0ad";
    internal const string TargetPlaytimeGoalsCommit = "fa959d3d4ffd09f7fd30e9ee8599aa5004b67033";
    internal static DateTime LoadedAtUtc { get; } = DateTime.UtcNow;
    public string Name => "ControlCenter";
    public Version Version => typeof(ControlCenterPlugin).Assembly.GetName().Version ?? new Version(1, 0, 0, 0);
    public Task OnLoaded() { ASF.ArchiLogger.LogGenericInfo($"ControlCenter {Version} loaded"); return Task.CompletedTask; }
}
