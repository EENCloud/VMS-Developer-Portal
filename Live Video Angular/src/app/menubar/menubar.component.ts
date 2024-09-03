import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-menubar',
  standalone: true,
  imports: [RouterModule],
  template: `
    <div class="navbar">
        <a [routerLink]="['/']">Home</a>
        <a [routerLink]="['/logout']">Logout</a>
    </div>
  `,
  styles: `
    .navbar {
        background-color: #238fce;
        overflow: hidden;
        padding: 10px 0;
    }

    .navbar a {
        float: left;
        display: block;
        color: #f2f2f2;
        text-align: center;
        padding: 14px 16px;
        text-decoration: none;
        font-size: 17px;
    }

    .navbar a:hover {
        background-color: #ddd;
        color: black;
    }
  `
})
export class MenubarComponent {}
