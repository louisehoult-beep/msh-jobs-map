import importlib.util, pathlib
here = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("a", here / "scripts/adapters/cranleigh-stem.py")
a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)
fx = here / "fixtures/adapters/cranleigh-stem"

p = a.parse((fx / "business-development-associate-8649.html").read_text(), "u")[0]
assert p["title"] == "Business Development Associate", p["title"]
assert p["industry"] == "Medical Devices"
assert p["jobLocation"]["address"]["addressLocality"] == "London - Central"
assert p["baseSalary"]["value"] == {"minValue": 28000.0, "maxValue": 35000.0}, p["baseSalary"]
assert p["employmentType"] == "PERMANENT" and p["identifier"] == "8649"
assert "pharmaceutical" in p["description"].lower()

assert a.parse((fx / "technical-sales-specialist-swine-8626.html").read_text(), "u") == []  # Rest of World (Mexico): skipped


p = a.parse((fx / "technical-sales-manager-sensors-8669.html").read_text(), "u")[0]
assert p["title"] == "Technical Sales Manager - Sensors"
assert a.parse("<html>nothing</html>", "u") == []
print("ok")
