import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from bot.catalog_admin import (
    CatalogAdminStorage, WEBAPP_DIR, normalize_catalog, product_revision,
    catalog_admin_edit_keyboard,
)


class CatalogAdminTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "catalog.json"
        self.initial = {
            "Напитки и сладости": {},
            "Бакалея": {"Семена": [{"name": "Чиа", "price": "100 руб.", "weight": "1 кг"}]},
            "Орехи": {"Орехи в глазури": [{"name": "Миндаль в глазури"}]},
            "Другой раздел": {"Прочее": [{"name": "Не терять"}]},
        }
        self.path.write_text(json.dumps(self.initial, ensure_ascii=False), encoding="utf-8")
        self.storage = CatalogAdminStorage(self.path)

    async def test_add_edit_delete_and_stale_buttons(self):
        catalog = await self.storage.read_catalog()
        category = list(catalog).index("Бобовые и семена")
        location, first = await self.storage.get_product(category, 0, 0)
        saved = await self.storage.add_product(category, 0, {"name": "Новый", "price": "200 руб.", "weight": "1 кг"})
        self.assertEqual(saved[0].product_index, 1)
        self.assertTrue(await self.storage.delete_product(category, 0, 0, product_revision(first)))
        # The old index now points at another product: neither deleting nor editing it is allowed.
        self.assertFalse(await self.storage.delete_product(category, 0, 0, product_revision(first)))
        self.assertIsNone(await self.storage.update_product_field(category_index=category, subcategory_index=0, product_index=0, field="name", value="Wrong", expected_revision=product_revision(first)))
        _, new = await self.storage.get_product(category, 0, 0)
        edited = await self.storage.update_product_field(category_index=category, subcategory_index=0, product_index=0, field="discount_percent", value=25, expected_revision=product_revision(new))
        self.assertEqual(edited[1]["discount_percent"], 25)
        self.assertTrue(edited[1]["promo"])
        for row in catalog_admin_edit_keyboard(location, edited[1]).inline_keyboard:
            for button in row:
                self.assertLessEqual(len(button.callback_data.encode()), 64)

    async def test_normalization_preserves_products_and_is_idempotent(self):
        catalog = await self.storage.read_catalog()
        self.assertEqual(sum(len(products) for subs in catalog.values() for products in subs.values()), 3)
        self.assertEqual(catalog["Орехи и фрукты в шоколаде"]["Шоколад и глазурь"][0]["name"], "Миндаль в глазури")
        layout = json.loads((WEBAPP_DIR / "catalog-layout.json").read_text())
        self.assertEqual(normalize_catalog(catalog, layout), catalog)

    async def test_corrupted_catalog_is_not_overwritten(self):
        self.path.write_text("broken", encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            await self.storage.add_product(0, 0, {"name": "New"})
        self.assertEqual(self.path.read_text(), "broken")

    async def test_section_crud_and_deleted_defaults_do_not_return(self):
        catalog = await self.storage.read_catalog()
        catalog = await self.storage.change_section("add", -1, -1, product_revision(catalog), "Новинки")
        index = list(catalog).index("Новинки")
        catalog = await self.storage.change_section("add", index, -1, product_revision(catalog), "Летнее")
        await self.storage.add_product(index, 0, {"name": "Новый товар"})
        catalog = await self.storage.read_catalog()
        catalog = await self.storage.change_section("rename", index, 0, product_revision(catalog), "Зимнее")
        self.assertEqual(catalog["Новинки"]["Зимнее"][0]["name"], "Новый товар")
        catalog = await self.storage.change_section("rename", index, -1, product_revision(catalog), "Новое")
        self.assertIn("Новое", catalog)
        catalog = await self.storage.change_section("delete", index, 0, product_revision(catalog))
        self.assertEqual(catalog["Новое"], {})
        index = list(catalog).index("Сухофрукты")
        old_revision = product_revision(catalog)
        catalog = await self.storage.change_section("delete", index, -1, old_revision)
        self.assertNotIn("Сухофрукты", await self.storage.read_catalog())
        with self.assertRaises(ValueError):
            await self.storage.change_section("delete", index, -1, old_revision)
        with self.assertRaises(ValueError):
            await self.storage.change_section("add", -1, -1, product_revision(catalog), "Новое")

    async def test_empty_catalog_can_start_again(self):
        self.path.write_text("{}")
        self.assertEqual(await self.storage.read_catalog(), {})
        catalog = await self.storage.change_section("add", -1, -1, product_revision({}), "Первый раздел")
        self.assertEqual(catalog, {"Первый раздел": {}})

    async def test_site_and_bot_use_identical_layout(self):
        jsc = Path("/System/Library/Frameworks/JavaScriptCore.framework/Versions/A/Helpers/jsc")
        if not jsc.exists():
            self.skipTest("JavaScriptCore unavailable")
        app = (WEBAPP_DIR / "app.js").read_text()
        function = app[app.index("function buildDisplayCatalog("):app.index("function pickFeaturedProducts(")]
        layout = json.loads((WEBAPP_DIR / "catalog-layout.json").read_text())
        raw = json.loads((WEBAPP_DIR / "catalog.json").read_text())
        script = "const catalogLayout=" + json.dumps(layout) + ";\n" + function + "\nprint(JSON.stringify(buildDisplayCatalog(" + json.dumps(raw) + ")));"
        result = subprocess.run([str(jsc), "-e", script], capture_output=True, text=True, check=True)
        site_catalog = json.loads(result.stdout)
        for subs in site_catalog.values():
            for products in subs.values():
                for product in products:
                    product.pop("rawCategory", None)
                    product.pop("rawSubcategory", None)
        self.assertEqual(site_catalog, normalize_catalog(raw, layout))


if __name__ == "__main__":
    unittest.main()
