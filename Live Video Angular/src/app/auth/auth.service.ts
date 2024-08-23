import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Router } from '@angular/router';
import { environment } from '../environments/environment';
import { Observable } from 'rxjs';
import { map, throwError } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private clientId = environment.clientId;
  private clientSecret = environment.clientSecret;
  private redirectUri = environment.redirectUri;

  constructor(private http: HttpClient, private router: Router) {}

  getAuthUrl(): string {
    const authBaseUrl = 'https://auth.eagleeyenetworks.com/oauth2/authorize';

    const params = {
      response_type: 'code',
      scope: 'vms.all',
      client_id: this.clientId,
      redirect_uri: this.redirectUri
    };

    const queryString = new URLSearchParams(params).toString();
    return `${authBaseUrl}?${queryString}`;
  }

  exchangeToken(token: string, type: 'authorization_code' | 'refresh_token' = 'authorization_code') {
    const tokenUrl = 'https://auth.eagleeyenetworks.com/oauth2/token';

    // Create headers with basic auth
    const authCredentials = btoa(`${this.clientId}:${this.clientSecret}`);

    const headers = new HttpHeaders({
      "accept": "application/json",
      "content-type": "application/x-www-form-urlencoded",
      "Authorization": `Basic ${authCredentials}`
    });

    // Construct body params based on the type of token exchange
    const bodyParams: { [key: string]: string } = {
      grant_type: type,
      scope: 'vms.all',
    };

    if (type === 'authorization_code') {
      bodyParams['code'] = token;
      bodyParams['redirect_uri'] = this.redirectUri;
    } else if (type === 'refresh_token') {
      bodyParams['refresh_token'] = token;
    }
    
    const body = new URLSearchParams(bodyParams);

    return this.http.post(tokenUrl, body.toString(), {
      headers: headers
    });
  }

  storeSession(authResponse: any) {
    localStorage.setItem('access_token', authResponse.access_token);
    localStorage.setItem('refresh_token', authResponse.refresh_token);
    localStorage.setItem('base_url', authResponse.httpsBaseUrl.hostname);
  }

  refreshToken(): Observable<void> {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      return throwError(() => new Error('No refresh token found'));
    }

    return this.exchangeToken(refreshToken, 'refresh_token').pipe(
      map((response: any) => {
        this.storeSession(response);
      })
    );
  }

  getAccessToken(): string {
    return localStorage.getItem('access_token') || '';
  }

  getBaseUrl(): string {
    return localStorage.getItem('base_url') || '';
  }

  logout() {
    localStorage.clear();
    this.router.navigate(['/login']);
  }

  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
  }
}

