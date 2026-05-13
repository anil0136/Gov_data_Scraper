from unittest.mock import patch

from django.test import SimpleTestCase

from bs4 import BeautifulSoup

from .mongo import MongoRecord
from .scrapers.scholarship import _parse_buddy4study_items, _parse_wemakescholars_cards
from .scrapers.tenders import _parse_tenderkart_cards, _parse_tendersontime_results
from .views import _is_displayable, _section


class TenderParserTests(SimpleTestCase):
    def test_parse_tendersontime_results(self):
        payload = {
            "searchdata": [
                {
                    "id": "140155027",
                    "Tender_Summery": "Providing Electrical Fixtures in the Police Building Tender Category Works",
                    "Country_Name_Known": "India",
                    "Posting_Date": "2026-04-25T20:50:47Z",
                    "Tender_Value": "INR 59071.00",
                    "Bid_Deadline_1": "2026-04-28T00:00:00Z",
                    "Tender_url": "https://www.tendersontime.com/india/details/example/",
                }
            ]
        }

        rows = _parse_tendersontime_results(payload, "https://www.tendersontime.com/tenders/")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source"], "TendersOnTime")
        self.assertEqual(rows[0]["external_id"], "140155027")
        self.assertEqual(rows[0]["category"], "Works")

    def test_parse_tenderkart_cards(self):
        html = """
        <div aria-label="Open tender: Road repair work for municipal area" role="link">
            <div>
                <div>
                    <h3><a href="/tender/example-uuid">MUNICIPAL AFFAIRS DEPARTMENT</a></h3>
                    <div>
                        <span>Purulia, West Bengal</span>
                        <span><span>Last activity</span> 25 Apr 2026</span>
                    </div>
                    <p>Road repair work for municipal area</p>
                </div>
                <div>
                    <span>West Bengal</span>
                    <div>AOC</div>
                    <span>Works</span>
                    <span>CIVIL WORKS</span>
                </div>
                <div>
                    <div>
                        <span>Awarded Bids (1)</span>
                        <span>ABC Infra</span>
                        <span>2.0 Lakh</span>
                    </div>
                </div>
            </div>
        </div>
        """

        rows = _parse_tenderkart_cards(
            BeautifulSoup(html, "html.parser"),
            "https://tenderkart.in/tenders/result",
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source"], "TenderKart")
        self.assertEqual(rows[0]["organization"], "MUNICIPAL AFFAIRS DEPARTMENT")
        self.assertEqual(rows[0]["status"], "AOC")
        self.assertEqual(rows[0]["procurement_type"], "Works")
        self.assertEqual(rows[0]["category"], "CIVIL WORKS")


class ScholarshipParserTests(SimpleTestCase):
    def test_parse_wemakescholars_cards(self):
        html = """
        <div class="post featured_post">
            <div class="sub-post clearfix">
                <div class="col-md-2">
                    <a href="/university/vanderbilt-university/scholarships">
                        <img class="internship-col-img" src="https://static.wemakescholars.com/images/scholarship-providers/737-photo.webp">
                    </a>
                </div>
                <div class="col-md-7 col-xs-12 col-sm-7 head-post-title icon-size">
                    <h2 class="post-title">
                        <a class="post-title" href="/scholarship/vanderbilt-university-scholarship">Vanderbilt University Scholarship 2026</a>
                    </h2>
                    <div class="row">
                        <div class="col-md-4 text-line-div">
                            <p class="text-line">Funding Type:</p>
                            <span>Only tuition fees</span>
                        </div>
                    </div>
                    <div class="row">
                        <div class="col-md-4 text-line-div">
                            <p class="text-line">Deadline:</p>
                            <span>30 Apr, 2026</span>
                        </div>
                    </div>
                    <div class="text-line-div">
                        <p class="text-line">Scholarship can be taken at:</p>
                        <span class="btn uni-btn font13">Vanderbilt University</span>
                    </div>
                </div>
            </div>
        </div>
        """

        rows = _parse_wemakescholars_cards(
            BeautifulSoup(html, "html.parser"),
            "https://www.wemakescholars.com/scholarship",
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["provider"], "Vanderbilt University")
        self.assertEqual(rows[0]["deadline"], "30 Apr, 2026")
        self.assertEqual(rows[0]["amount"], "Only tuition fees")
        self.assertIn("737-photo.webp", rows[0]["image_url"])

    def test_parse_buddy4study_items(self):
        rows = _parse_buddy4study_items([
            {
                "deadlineDate": "2026-05-21",
                "scholarshipName": "College Board 90% Fee Waiver Program",
                "logoFid": "https://cdn.example.com/logo.jpeg",
                "slug": "college-board-90-fee-waiver-program",
                "pageSlug": "scholarship/college-board-90-fee-waiver-program",
                "scholarshipMultilinguals": [
                    {
                        "title": "College Board 90% Fee Waiver Program",
                        "purposeAward": "Tuition fee waiver",
                    }
                ],
            }
        ])

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["provider"], "Buddy4Study")
        self.assertEqual(rows[0]["deadline"], "2026-05-21")
        self.assertEqual(rows[0]["amount"], "Tuition fee waiver")
        self.assertEqual(rows[0]["image_url"], "https://cdn.example.com/logo.jpeg")


class ScholarshipDisplayTests(SimpleTestCase):
    def test_hide_old_listing_page_noise(self):
        item = MongoRecord(
            "scholarships",
            {
                "title": "By Subject",
                "provider": "",
                "deadline": "",
                "amount": "",
                "image_url": "",
                "url": "https://www.wemakescholars.com/scholarship",
            },
        )
        self.assertFalse(_is_displayable(item))

    def test_show_real_scholarship_without_logo(self):
        item = MongoRecord(
            "scholarships",
            {
                "title": "Google Phd Fellowship India Program 2026",
                "provider": "Buddy4Study",
                "deadline": "",
                "amount": "Up to USD 50,000",
                "image_url": "",
                "url": "https://www.buddy4study.com/scholarship/google-phd-fellowship-india-program-2026",
            },
        )
        self.assertTrue(_is_displayable(item))


class DashboardSectionTests(SimpleTestCase):
    def test_hidden_count_only_counts_loaded_preview_noise(self):
        records = [
            MongoRecord(
                "gov",
                {
                    "_id": "gov-1",
                    "title": "Apply for example service",
                    "service_type": "Online",
                    "department": "Example Department",
                    "description": "Example description",
                    "url": "https://example.com/service",
                },
            ),
            MongoRecord(
                "gov",
                {
                    "_id": "gov-2",
                    "title": "HomeAll Categories",
                    "service_type": "",
                    "department": "",
                    "description": "",
                    "url": "https://example.com/noise",
                },
            ),
        ]

        with patch("scraper.views.count_records", return_value=25000), patch(
            "scraper.views.latest_records",
            return_value=records,
        ):
            section = _section("Government Services", "gov")

        self.assertEqual(section["total_count"], 25000)
        self.assertEqual(section["checked_count"], 2)
        self.assertEqual(section["clean_count"], 1)
        self.assertEqual(section["hidden_count"], 1)


class SchemeApiTests(SimpleTestCase):
    def test_api_index_lists_scheme_urls(self):
        response = self.client.get("/api/")

        self.assertEqual(response.status_code, 200)
        endpoints = response.json()["endpoints"]
        card_endpoints = response.json()["card_endpoints"]
        self.assertIn("umang_schemes", endpoints)
        self.assertIn("government_services", endpoints)
        self.assertIn("myscheme", endpoints)
        self.assertIn("india_portal_schemes", endpoints)
        self.assertIn("scholarships", endpoints)
        self.assertIn("grants", endpoints)
        self.assertIn("tenders", endpoints)
        self.assertIn("scraper_status", endpoints)
        self.assertIn("banking_financial_services_and_insurance", card_endpoints)
        self.assertIn("scholarships", card_endpoints)

    def test_government_services_api_returns_saved_rows(self):
        records = [
            MongoRecord(
                "gov",
                {
                    "_id": "gov-1",
                    "title": "Apply for example service",
                    "service_type": "Online",
                    "department": "Example Department",
                    "description": "Example description",
                    "url": "https://example.com/service",
                },
            )
        ]

        with patch("scraper.views.latest_records", return_value=records):
            response = self.client.get("/api/government-services/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"], "Government Services")
        self.assertEqual(payload["api_key"], "government_services")
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["results"][0]["title"], "Apply for example service")
        self.assertEqual(payload["results"][0]["url"], "https://example.com/service")

    def test_government_services_api_filters_background_noise(self):
        records = [
            MongoRecord(
                "gov",
                {
                    "_id": "gov-1",
                    "title": "Apply for example service",
                    "service_type": "Online",
                    "department": "Example Department",
                    "description": "Example description",
                    "url": "https://example.com/service",
                },
            ),
            MongoRecord(
                "gov",
                {
                    "_id": "gov-2",
                    "title": "HomeAll Categories",
                    "service_type": "",
                    "department": "",
                    "description": "",
                    "url": "https://example.com/noise",
                },
            ),
        ]

        with patch("scraper.views.latest_records", return_value=records):
            response = self.client.get("/api/government-services/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["results"][0]["title"], "Apply for example service")

    def test_myscheme_api_includes_detail_fields(self):
        records = [
            MongoRecord(
                "myscheme",
                {
                    "_id": "myscheme-1",
                    "title": "Example myScheme",
                    "description": "Description",
                    "eligibility": "Eligibility",
                    "benefits": "Benefits",
                    "category": "Category",
                    "ministry": "Ministry",
                    "department": "Department",
                    "level": "State",
                    "tags": "tag",
                    "application_process": "Apply online",
                    "documents": "Documents",
                    "references": "References",
                    "raw_data": {"source": "test"},
                    "url": "https://example.com/myscheme",
                },
            )
        ]

        with patch("scraper.views.latest_records", return_value=records):
            response = self.client.get("/api/myscheme/")

        self.assertEqual(response.status_code, 200)
        result = response.json()["results"][0]
        self.assertEqual(result["eligibility"], "Eligibility")
        self.assertEqual(result["raw_data"], {"source": "test"})

    def test_scraper_status_api_returns_progress(self):
        with patch(
            "scraper.views.get_scraper_status",
            return_value={
                "enabled": True,
                "is_running": True,
                "cycle": 2,
                "processed": 5,
                "total": 10,
                "percent": 50,
                "current_source": "GOV",
                "current_url": "https://example.com",
                "message": "Scraping GOV...",
                "last_started_at": "2026-05-13T07:30:00Z",
                "last_completed_at": "",
                "next_run_at": "",
                "error": "",
            },
        ):
            response = self.client.get("/api/scraper-status/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["percent"], 50)
        self.assertTrue(payload["is_running"])
        self.assertEqual(payload["current_source"], "GOV")

    def test_card_api_returns_matching_records_with_api_key(self):
        def records_for_kind(kind):
            if kind == "myscheme":
                return [
                    MongoRecord(
                        "myscheme",
                        {
                            "_id": "myscheme-1",
                            "title": "Crop insurance support",
                            "description": "Insurance support for farmers",
                            "eligibility": "Farmers",
                            "benefits": "Premium support",
                            "category": "Agriculture",
                            "ministry": "Ministry",
                            "department": "Department",
                            "level": "Central",
                            "tags": "farmer crop",
                            "application_process": "Apply online",
                            "documents": "Documents",
                            "references": "References",
                            "raw_data": {},
                            "url": "https://example.com/crop",
                        },
                    )
                ]
            return []

        with patch("scraper.views.latest_records", side_effect=records_for_kind):
            response = self.client.get("/api/cards/agriculture/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["api_key"], "agriculture")
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["results"][0]["source_key"], "myscheme")
        self.assertEqual(payload["results"][0]["title"], "Crop insurance support")

    def test_card_api_accepts_api_key_in_url(self):
        with patch("scraper.views.latest_records", return_value=[]):
            response = self.client.get("/api/cards/banking_financial_services_and_insurance/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["api_key"], "banking_financial_services_and_insurance")

    def test_unknown_card_api_returns_404(self):
        response = self.client.get("/api/cards/unknown-card/")

        self.assertEqual(response.status_code, 404)

# Create your tests here.
