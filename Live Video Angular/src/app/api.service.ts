import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpErrorResponse } from '@angular/common/http';
import { AuthService } from './auth/auth.service';
import { catchError, map, switchMap, throwError } from 'rxjs';
import { Observable, of } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ApiService {

  constructor(
    private http: HttpClient,
    private authService: AuthService
  ) { }

  private handleResponse<T>(request: Observable<T>): Observable<T> {
    return request.pipe(
      catchError((error: HttpErrorResponse) => {
        if (error.status === 401) {
          // Refresh token and retry request
          console.log('Auth failed. Refreshing access token');
          return this.authService.refreshToken().pipe(
            switchMap(() => {
              // Retry request
              return request;
            })
          );
        } else {
          return throwError(() => error);
        }
      })
    );
  }

  private get baseUrl(): string {
    return `https://${this.authService.getBaseUrl()}/api/v3.0`;
  }

  getAccessToken(): string {
    return this.authService.getAccessToken();
  }

  getBaseUrl(): string {
    return this.authService.getBaseUrl();
  }

  apiCall<T>(
    endpoint: string,
    method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET',
    headers?: HttpHeaders,
    params?: any,
    data?: any
  ): Observable<T> {
    const url = `${this.baseUrl}${endpoint}`;
    console.log('API Call', method, url);
    let headersToSend = headers || new HttpHeaders();
    headersToSend = headersToSend.set(
      'Authorization', `Bearer ${this.authService.getAccessToken()}`);

    if (method === 'GET') {
      return this.handleResponse(
        this.http.get<T>(
          url, { headers: headersToSend, params: params }
        )
      );
    } else if (method === 'POST') {
      return this.handleResponse(
        this.http.post<T>(
          url, data, { headers: headersToSend, params: params }
        )
      );
    }

    return throwError(() => new Error('Method not supported'));
  }

  getCameras(cameraId: string | null): Observable<any> {
    if (cameraId) {
      return this.apiCall(`/cameras/${cameraId}`);
    } else {
      return this.apiCall('/cameras');
    }
  }

  getFeeds(
    deviceId: string | null,
    type: string = "preview",
    include: string = "multipartUrl"
  ): Observable<any> {
    const endpoint = "/feeds";

    const params: { [key: string]: string } = {
      type: type,
      include: include
    };

    if (deviceId) {
      params['deviceId'] = deviceId;
    }
    
    return this.apiCall(endpoint, 'GET', undefined, params);
  }
}
