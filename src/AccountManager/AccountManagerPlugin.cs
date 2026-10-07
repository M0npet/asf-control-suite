using System;
using System.Composition;
using System.Threading.Tasks;
using ArchiSteamFarm.Core;
using ArchiSteamFarm.Plugins.Interfaces;
using JetBrains.Annotations;

namespace AccountManager;

[Export(typeof(IPlugin))]
[UsedImplicitly]
internal sealed class AccountManagerPlugin : IPlugin {
    internal static DefaultsStore Defaults { get; } = new();

    public string Name => "AccountManager";

    public Version Version =>
        typeof(AccountManagerPlugin).Assembly.GetName().Version
        ?? new Version(1, 1, 0, 0);

    public Task OnLoaded() {
        ASF.ArchiLogger.LogGenericInfo($"AccountManager {Version} loaded");
        return Task.CompletedTask;
    }
}
