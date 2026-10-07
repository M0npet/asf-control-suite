using System;
using System.IO;
using System.Linq;
using Microsoft.AspNetCore.Mvc;

namespace ControlWeb;

[ApiController]
[Route("Api/ControlWeb")]
public sealed class ControlWebController : ControllerBase {
    [HttpGet("LogTail")]
    public IActionResult GetLogTail([FromQuery] int lines = 200) {
        int count = Math.Clamp(lines, 20, 1000);
        string path = Path.Combine(AppContext.BaseDirectory, "log.txt");

        string[] tail = File.Exists(path)
            ? File.ReadLines(path).TakeLast(count).ToArray()
            : Array.Empty<string>();

        return Ok(new {
            Success = true,
            Message = (string?) null,
            Result = new {
                Lines = tail,
                Count = tail.Length
            }
        });
    }
}
