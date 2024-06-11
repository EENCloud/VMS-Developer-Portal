/*
	 Get API Credentials using OAuth2
		Step 1: Redirect the user to auth.eagleeyenetworks.com
		Step 2: The user will log in to their VMS Account
		Step 3: The user will be redirected back to your application with a CODE
		Step 4: Your application backend/server request the Access token.
*/
package main

// We'll use Fiber to start an HTTP server to act as your application backend.
import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"

	"github.com/gofiber/fiber/v2"
)

// Enter the OAuth client credentials for your application.
// For more info see:
// https://developer.eagleeyenetworks.com/docs/client-credentials
// To use the API, your appliction needs its own client credentials.
const (
	hostName     = "127.0.0.1"
	port         = 3333
	clientId     = "{Your Client ID}"
	clientSecret = "{Your Client Secret}"
)

// A refresh token can be used to get a new access token when the current one expires.
// Critically, this avoids the need for the user to log in again.
// This is useful for long-running applications.
var refreshToken = ""

// This method is executing step 3.
// It will request the access token and refresh token.
// The redirect_uri here must match the redirect_uri sent in step 1.
func getTokens(code string) (string, error) {
	baseURL := "https://auth.eagleeyenetworks.com/oauth2/token"
	data := url.Values{}
	data.Set("grant_type", "authorization_code")
	data.Set("scope", "vms.all")
	data.Set("code", code)
	data.Set("redirect_uri", fmt.Sprintf("http://%s:%d", hostName, port))

	req, err := http.NewRequest("POST", baseURL, bytes.NewBufferString(data.Encode()))
	if err != nil {
		return "", err
	}
	req.SetBasicAuth(clientId, clientSecret)
	req.Header.Add("Content-Type", "application/x-www-form-urlencoded")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&result)

	responseText, err := json.Marshal(result)
	if err != nil {
		return "", err
	}

	return string(responseText), nil
}

// Use a refresh token to get a new access token
func refreshTokenRequest(refreshToken string) (string, error) {
	baseURL := "https://auth.eagleeyenetworks.com/oauth2/token"
	data := url.Values{}
	data.Set("grant_type", "refresh_token")
	data.Set("scope", "vms.all")
	data.Set("refresh_token", refreshToken)

	req, err := http.NewRequest("POST", baseURL, bytes.NewBufferString(data.Encode()))
	if err != nil {
		return "", err
	}
	req.SetBasicAuth(clientId, clientSecret)
	req.Header.Add("Content-Type", "application/x-www-form-urlencoded")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&result)

	responseText, err := json.Marshal(result)
	if err != nil {
		return "", err
	}

	return string(responseText), nil
}

func oauthValid(oauthObject string) bool {
	var jsonObject map[string]interface{}
	if err := json.Unmarshal([]byte(oauthObject), &jsonObject); err != nil {
		return false
	}
	_, exists := jsonObject["access_token"]
	return exists
}

func main() {
	app := fiber.New()

	/*
		If a user visits localhost:3333 this method will be called.
		1) For step 1, a link is given to rediret the user to
		auth.eagleeyenetworks.com.
		Here, they can log in to their VMS account.
		2) Once the user logs in, they will be redirected back to
		localhost:3333 with a CODE. The backend can now request
		the access_token and refresh_token.
		3) If a refresh_token is stored, it can be used to get a new
		new access_token without requiring the user to to log in again.
	*/
	app.Get("/", func(c *fiber.Ctx) error {

		// This is getting the ?code= querystring value from the HTTP request.
		code := c.Query("code")

		if code != "" {
			// Execute Step 2, the user is redirected back to localhost:3333
			// because of the "&redirect_uri="
			// With the CODE, this backend can request the actual access_token and
			// refresh_token. For demonstration purposes the results are printed to
			// the console.
			// On production, never show the refresh_token in the browser.
			oauthObject, err := getTokens(code)
			if err != nil {
				return c.Status(fiber.StatusInternalServerError).SendString(fmt.Sprintf("Error getting tokens: %v", err))
			}

			if oauthValid(oauthObject) {
				fmt.Println(oauthObject)
				return c.SendString("You are logged in")
			} else {
				fmt.Println("Code Auth failed. Response: " + oauthObject)
				return c.Status(fiber.StatusUnauthorized).SendString("Code Auth failed")
			}
		} else if refreshToken != "" {
			oauthObject, err := refreshTokenRequest(refreshToken)
			if err != nil {
				return c.Status(fiber.StatusInternalServerError).SendString(fmt.Sprintf("Error refreshing token: %v", err))
			}

			if oauthValid(oauthObject) {
				fmt.Println(oauthObject)
				return c.SendString("You are logged in thanks to a refresh token.")
			} else {
				fmt.Println("Refresh token failed. Response: " + oauthObject)
				return c.Status(fiber.StatusUnauthorized).SendString("Refresh token failed")
			}
		}

		// Executing step 1, a link is generated to redirect the user to
		// auth.eagleeyenetworks.com
		endpoint := "https://auth.eagleeyenetworks.com/oauth2/authorize"
		requestAuthUrl := fmt.Sprintf("%s?client_id=%s&response_type=code&scope=vms.all&redirect_uri=http://%s:%d", endpoint, clientId, hostName, port)
		page := fmt.Sprintf(`
		<html><head><title>OAuth Testing</title></head>
		<h1>OAuth Testing</h1>
		</br>
		<a href='%s'>Login with Eagle Eye Networks</a>
		</html>`, requestAuthUrl)
		c.Set("Content-Type", "text/html")
		return c.SendString(page)
	})

	// Start the server
	app.Listen(fmt.Sprintf(":%d", port))
}
