<?php

// Load environment variables
require 'vendor/autoload.php';
use Dotenv\Dotenv;

$dotenv = Dotenv::createImmutable(__DIR__);
$dotenv->load();

// Enter the OAuth client credentials for your application.
$clientId = $_ENV['CLIENT_ID'];
$clientSecret = $_ENV['CLIENT_SECRET'];

// Hostname and port for the HTTP server
$hostName = "127.0.0.1";
$port = 3333;

// A refresh token can be used to get a new access token
// without the user having to log in again.
// If you have a refresh token, you can enter it here.
$refreshToken = "";

// This method is executing step 3.
// It will request the access token and refresh token.
// The redirect_uri here must match the redirect_uri sent in step 1.
function getTokens($code) {
    global $clientId, $clientSecret, $hostName, $port;
    $url = "https://auth.eagleeyenetworks.com/oauth2/token?grant_type=authorization_code&scope=vms.all&code=" . $code . "&redirect_uri=http://" . $hostName . ":" . $port;
    
    $context = stream_context_create([
        'http' => [
            'method' => 'POST',
            'header' => "Authorization: Basic " . base64_encode($clientId . ":" . $clientSecret) . "\r\n" .
                        "Content-Type: application/x-www-form-urlencoded\r\n",
            'content' => ''
        ]
    ]);
    
    $response = file_get_contents($url, false, $context);
    return $response;
}

// Use a refresh token to get a new access token
function refreshToken($refreshToken) {
    global $clientId, $clientSecret;
    $url = "https://auth.eagleeyenetworks.com/oauth2/token?grant_type=refresh_token&scope=vms.all&refresh_token=" . $refreshToken;
    
    $context = stream_context_create([
        'http' => [
            'method' => 'POST',
            'header' => "Authorization: Basic " . base64_encode($clientId . ":" . $clientSecret) . "\r\n" .
                        "Content-Type: application/x-www-form-urlencoded\r\n",
            'content' => ''
        ]
    ]);
    
    $response = file_get_contents($url, false, $context);
    return $response;
}

function oauthValid($oauthObject) {
    $json_object = json_decode($oauthObject, true);
    if ($json_object === null) {
        return false;
    }
    
    return isset($json_object['access_token']);
}

function index() {
    global $clientId, $hostName, $port, $refreshToken;

    if (isset($_GET['code'])) {
        $code = $_GET['code'];
        $oauthObject = getTokens($code);
        if (oauthValid($oauthObject)) {
            echo $oauthObject;
            return "You are logged in";
        } else {
            echo "Code Auth failed. Response: " . $oauthObject;
        }
    } elseif (!empty($refreshToken)) {
        $oauthObject = refreshToken($refreshToken);
        if (oauthValid($oauthObject)) {
            echo $oauthObject;
            return "You are logged in thanks to a refresh token.";
        } else {
            echo "Refresh token failed. Response: " . $oauthObject;
        }
    }

    $endpoint = "https://auth.eagleeyenetworks.com/oauth2/authorize";
    $requestAuthUrl = $endpoint . "?client_id=" . $clientId . "&response_type=code&scope=vms.all&redirect_uri=http://" . $hostName . ":" . $port;

    $page = "
    <html><head><title>OAuth Testing</title></head>
    <h1>OAuth Testing</h1>
    </br>
    <a href='{$requestAuthUrl}'>Login with Eagle Eye Networks</a>
    </html>";
    return $page;
}

echo index();

?>
