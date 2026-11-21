# Primary technical references consulted

- [SEC submissions API and historical-file metadata](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [SEC developer resources and fair access](https://www.sec.gov/about/developer-resources)
- [SEC webmaster FAQ: header acceptance timestamps and no first-availability timestamp](https://www.sec.gov/about/webmaster-frequently-asked-questions)
- [yfinance download API: adjustment settings and exclusive end date](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html)
- [exchange_calendars package and XNYS session API](https://pypi.org/project/exchange_calendars/)
- [statsmodels cluster covariance reference](https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_cluster.html)
- [yfinance source README and data-rights note](https://github.com/ranaroussi/yfinance#download-market-data-from-yahoo-finances-api)

Implementation is checked against cached primary SEC responses, not assumptions about API
timezone labels. No third-party timestamp claim is treated as event-level verification.

