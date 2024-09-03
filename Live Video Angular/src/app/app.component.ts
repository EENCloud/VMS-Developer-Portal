import {Component} from '@angular/core';
import {ViewerComponent} from './viewer/viewer.component';
import {LoginComponent} from './login/login.component';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    ViewerComponent,
    LoginComponent,
    RouterModule,
  ],
  template: `
      <router-outlet></router-outlet>
  `,
  styleUrls: ['./app.component.css'],
})
export class AppComponent {
  title = 'Eagle Eye Live View';
}


