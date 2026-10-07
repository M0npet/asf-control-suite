using System;
using System.Composition;
using System.Threading.Tasks;
using ArchiSteamFarm.Core;
using ArchiSteamFarm.Plugins.Interfaces;
using JetBrains.Annotations;

namespace ControlWeb;

[Export(typeof(IPlugin))]
[UsedImplicitly]
internal sealed class ControlWebPlugin : IPlugin, IWebInterface {
    public string Name => "ControlWeb";

    public Version Version =>
        typeof(ControlWebPlugin).Assembly.GetName().Version
        ?? new Version(1, 1, 0, 0);

    public string PhysicalPath => "www";

    public string WebPath => "/Control";

    public Task OnLoaded() {
        ASF.ArchiLogger.LogGenericInfo($"ControlWeb {Version} loaded at {WebPath}");
        return Task.CompletedTask;
    }
}
