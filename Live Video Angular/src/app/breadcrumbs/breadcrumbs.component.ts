import { Component, OnInit } from '@angular/core';
import { RouterModule, Router, ActivatedRoute, NavigationEnd } from '@angular/router';
import { filter, map } from 'rxjs/operators'
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-breadcrumbs',
  standalone: true,
  imports: [RouterModule, CommonModule],
  template: `
    <nav *ngIf='breadcrumbs.length'>
      <ul>
        <li *ngFor='let breadcrumb of breadcrumbs; let last = last'>
          <a *ngIf='!last' [routerLink]="breadcrumb.url"]>{{ breadcrumb.label }}</a>
          <span *ngIf='last'>{{ breadcrumb.label }}</span>
        </li>
      </ul>
    </nav>
  `,
  styles: `
    .breadcrumb {
        margin: 20px 0;
        padding: 10px 0;
        text-align: left;
    }

    .breadcrumb a {
        color: #238fce;
        text-decoration: none;
        padding: 0 10px;
    }

    .breadcrumb a:hover {
        text-decoration: underline;
    }
  `
})
export class BreadcrumbsComponent  implements OnInit {
  breadcrumbs: Array<{ label: string, url: string }> = [];

  constructor(
    private router: Router,
    private route: ActivatedRoute
  ) {}

  ngOnInit() {
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd),
      map(() => this.buildBreadcrumbs(this.route.root))
    ).subscribe(breadcrumbs => {
      this.breadcrumbs = breadcrumbs;
    });
  }

  private buildBreadcrumbs(route: ActivatedRoute, url: string = '', breadcrumbs: Array<{ label: string, url: string }> = []): Array<{ label: string, url: string }> {
    const children: ActivatedRoute[] = route.children;

    if (children.length === 0) {
      return breadcrumbs;
    }

    for (let child of children) {
      const routeURL: string = child.snapshot.url.map(segment => segment.path).join('/');
      if (routeURL !== '') {
        url += `/${routeURL}`;
      }

      const label = child.snapshot.data['breadcrumb'];
      if (label) {
        breadcrumbs.push({ label, url });
      }

      return this.buildBreadcrumbs(child, url, breadcrumbs);
    }

    return breadcrumbs;
  }

}
