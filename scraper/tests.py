from django.test import TestCase

from bs4 import BeautifulSoup

from .scrapers.scholarship import _parse_buddy4study_items, _parse_wemakescholars_cards
from .scrapers.tenders import _parse_tenderkart_cards, _parse_tendersontime_results
from .views import _is_displayable
from .models import Scholarship


class TenderParserTests(TestCase):
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


class ScholarshipParserTests(TestCase):
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


class ScholarshipDisplayTests(TestCase):
    def test_hide_old_listing_page_noise(self):
        item = Scholarship(
            title="By Subject",
            provider="",
            deadline="",
            amount="",
            image_url="",
            url="https://www.wemakescholars.com/scholarship",
        )
        self.assertFalse(_is_displayable(item))

    def test_show_real_scholarship_without_logo(self):
        item = Scholarship(
            title="Google Phd Fellowship India Program 2026",
            provider="Buddy4Study",
            deadline="",
            amount="Up to USD 50,000",
            image_url="",
            url="https://www.buddy4study.com/scholarship/google-phd-fellowship-india-program-2026",
        )
        self.assertTrue(_is_displayable(item))

# Create your tests here.
