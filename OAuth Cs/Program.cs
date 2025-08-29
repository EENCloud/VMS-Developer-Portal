using System.Net.Http.Headers;
using Microsoft.AspNetCore.WebUtilities;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Hosting;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

string hostName     = "127.0.0.1";
int port            = 3333;
string clientId     = "<your clientId>";
string clientSecret = "<your clientSecret>";


async Task<string> GetTokens(string code)
{
    using var client = new HttpClient();

    var request = new HttpRequestMessage(HttpMethod.Post, "https://auth.eagleeyenetworks.com/oauth2/token");
    var parameters = new List<KeyValuePair<string, string>>
    {
        new("grant_type", "authorization_code"),
        new("scope", "vms.all"),
        new("code", code),
        new("redirect_uri", $"http://{hostName}:{port}")
    };
    request.Content = new FormUrlEncodedContent(parameters);

    var byteArray = System.Text.Encoding.ASCII.GetBytes($"{clientId}:{clientSecret}");
    request.Headers.Authorization = new AuthenticationHeaderValue("Basic", Convert.ToBase64String(byteArray));

    var response = await client.SendAsync(request);
    return await response.Content.ReadAsStringAsync();
}

app.MapGet("/", async (HttpContext context) =>
{
    var query = context.Request.Query;
    if (query.ContainsKey("code"))
    {
        string code = query["code"];
        string oauthObject = await GetTokens(code);
        Console.WriteLine(oauthObject);
        await context.Response.WriteAsync("You are logged in");
    }
    else
    {
        var queryParams = new Dictionary<string, string?>
        {
            ["client_id"] = clientId,
            ["response_type"] = "code",
            ["scope"] = "vms.all",
            ["redirect_uri"] = $"http://{hostName}:{port}"
        };

        string url = QueryHelpers.AddQueryString("https://auth.eagleeyenetworks.com/oauth2/authorize", queryParams);
        await context.Response.WriteAsync($"<a href='{url}'>Login with Eagle Eye Networks</a>");
    }
});

app.Run($"http://{hostName}:{port}");
