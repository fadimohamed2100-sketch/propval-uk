"""
Downloads Land Registry Price Paid 2024 data and loads into sales_transactions.
Run: python seeder/load_land_registry.py
"""
import asyncio, csv, io, httpx, os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DATABASE_URL = os.environ["DATABASE_URL"]
LR_URL = "https://use-land-property-data.service.gov.uk/datasets/ppd/downloads/pp-2024.csv"

async def main():
    print("Downloading Land Registry 2024 data...")
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.get(LR_URL)
        data = resp.text

    engine = create_async_engine(DATABASE_URL)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    rows = list(csv.reader(io.StringIO(data)))
    print(f"Loaded {len(rows)} rows. Inserting...")

    async with Session() as session:
        inserted = 0
        for i, r in enumerate(rows):
            if len(r) < 10:
                continue
            try:
                await session.execute(text("""
                    INSERT INTO sales_transactions
                        (id, address, postcode, price_pence, transaction_date, property_type, source, source_ref)
                    VALUES
                        (gen_random_uuid(),
                         :address, :postcode, :price, :date, :ptype, 'land_registry', :ref)
                    ON CONFLICT (source_ref) DO NOTHING
                """), {
                    "address": f"{r[7]} {r[9]}".strip(),
                    "postcode": r[3].strip(),
                    "price": int(float(r[1])) * 100,
                    "date": r[2][:10],
                    "ptype": {"D":"detached","S":"semi_detached","T":"terraced","F":"flat"}.get(r[4], "other"),
                    "ref": r[0].strip("{}")
                })
                inserted += 1
                if inserted % 10000 == 0:
                    await session.commit()
                    print(f"  {inserted} rows inserted...")
            except Exception as e:
                continue
        await session.commit()
    print(f"Done! {inserted} transactions loaded.")

asyncio.run(main())
