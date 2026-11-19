import unittest
from unittest.mock import patch, Mock

from app.rag.tools import PublishedPropertyRepository, _public_text
from app.rag.config import Settings


class PublicPropertyProjectionTests(unittest.TestCase):
    def test_public_text_redacts_contact_and_internal_markers(self):
        text = _public_text(
            "<b>Liên hệ 0905 123 456 hoặc a@example.com</b> UNVERIFIED TINIX_AI"
        )
        for forbidden in ("0905", "a@example.com", "UNVERIFIED", "TINIX_AI"):
            self.assertNotIn(forbidden, text)

    def test_public_row_never_exposes_private_columns(self):
        repository = PublishedPropertyRepository(Settings())
        uid='00000000-0000-4000-8000-000000000001'
        row={'id':uid,'status':'PUBLISHED','listingCode':'SP001','title':'Nhà thử 0905 123 456',
             'owner_id':42,'contact_phone':'0905 123 456','storage_key':'private',
             'images':[{'id':'image-1','url':f'/api/v1/properties/{uid}/images/image-1/content'}]}
        client=Mock();client.get.return_value.status_code=200
        client.get.return_value.json.return_value={'items':[row],'totalPages':1}
        with patch('app.rag.tools.httpx.Client') as factory:
            factory.return_value.__enter__.return_value=client
            public=repository.list_public_images()[0]
        for forbidden in ("owner_id", "contact_phone", "contact_email", "uploaded_by",
                          "storage_key", "review_reason", "sha256"):
            self.assertNotIn(forbidden, public)
        self.assertEqual(public["listingCode"], "SP001")
        self.assertNotIn('0905',public['title'])

    def test_image_catalog_keeps_cloudinary_and_rejects_other_origins(self):
        uid='00000000-0000-4000-8000-000000000001'
        client=Mock();client.get.return_value.status_code=200
        client.get.return_value.json.return_value={'items':[{'id':uid,'status':'PUBLISHED','images':[
            {'id':'approved','url':'https://res.cloudinary.com/demo/image/upload/sample.jpg'},
            {'id':'blocked','url':'https://res.cloudinary.com.evil.example/sample.jpg'},
            {'id':'private','url':'http://127.0.0.1:9999/private'}]}],'totalPages':1}
        with patch('app.rag.tools.httpx.Client') as factory:
            factory.return_value.__enter__.return_value=client
            result=PublishedPropertyRepository(Settings()).list_public_images()
        self.assertEqual([item['imageId'] for item in result],['approved'])


if __name__ == "__main__":
    unittest.main()
