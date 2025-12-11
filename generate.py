"""
Generate Trip Itinerary PDF
FULLY CORRECTED to match actual Pydantic schemas

Usage: python generate_itinerary.py
Output: outputs/bali_itinerary_20260715.pdf
"""

import asyncio
import sys
import os
from datetime import date

sys.path.insert(0, '/Users/vincent/Downloads/tripcraft-lite 2')

from backend.models.schemas import TripRequest, TripPreferences
from backend.orchestrator.trip_orchestrator import TripOrchestrator
from backend.utils.pdf_generator import generate_trip_pdf


def print_header(text: str):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")


async def main():
    """Main function to generate trip itinerary PDF"""
    
    print_header("🌍 TRIPCRAFT PDF GENERATOR")
    
    
    # ========================================
    # HARDCODED INPUT - CORRECT SCHEMA
    # ========================================
    
    trip_request = TripRequest(
        destination="Jakarta",
        origin="Surabaya",
        start_date=date(2026, 2, 4),
        end_date=date(2026, 2, 25),
        budget=100000000000.0,
        travelers=2,
        preferences=TripPreferences(
            accommodation="mid-range",
            interests=["shopping", "culture", "food"],
            dietary_restrictions=[],
            pace="moderate"
        )
    )
    
    # ========================================
    # GENERATE TRIP PLAN
    # ========================================
    
    print("\n⏳ Generating trip plan...")
    print("   This will take 10-15 seconds (calling Amadeus API)\n")
    
    orchestrator = TripOrchestrator()
    
    def on_progress(progress):
        percentage = progress.get_progress_percentage()
        if progress.messages:
            print(f"   [{percentage:5.1f}%] {progress.messages[-1]}")
    
    trip_plan, metadata = await orchestrator.plan_trip(
        trip_request,
        progress_callback=on_progress
    )
    
    print(f"\n Trip planning completed in {metadata.get('execution_time_seconds', 0):.1f}s")
    
    # ========================================
    # PRINT SUMMARY - CORRECT ATTRIBUTES
    # ========================================
    
    print_header("📊 TRIP PLAN SUMMARY")
    
    # CORRECT: destination is DestinationInfo object with .name attribute
    print(f" Destination: {trip_plan.destination.destination.name}")
    print(f" Duration: {len(trip_plan.itinerary.days)} days")
    print(f" Travelers: {trip_request.travelers} people")
    print()
    
    print(" BUDGET:")
    print(f"   Total Cost: Rp {trip_plan.budget.breakdown.total:,.0f}")
    print(f"   Remaining: Rp {trip_plan.budget.breakdown.remaining:,.0f}")
    print(f"   Status: {' Within budget' if trip_plan.budget.is_within_budget else '⚠️ Over budget'}")
    print()
    
    print(" FLIGHTS:")
    print(f"   Source: {trip_plan.flights.data_source}")
    print(f"   Cost: Rp {trip_plan.flights.total_flight_cost:,.0f}")
    if trip_plan.flights.recommended_outbound:
        print(f"   Outbound: {trip_plan.flights.recommended_outbound.airline} "
              f"{trip_plan.flights.recommended_outbound.flight_number}")
    print()
    
    print(" HOTEL:")
    if trip_plan.hotels.recommended_hotel:
        print(f"   Name: {trip_plan.hotels.recommended_hotel.name}")
        print(f"   Rating: {trip_plan.hotels.recommended_hotel.rating}⭐")
    print(f"   Cost: Rp {trip_plan.hotels.total_accommodation_cost:,.0f}")
    print()
    
    print(" DINING:")
    print(f"   Meals planned: {len(trip_plan.dining.meal_plan)} days")
    print(f"   Cost: Rp {trip_plan.dining.estimated_total_cost:,.0f}")
    print()
    
    print(" CONFIDENCE:")
    print(f"   Overall: {trip_plan.overall_confidence:.2%}")
    print()
    
    if trip_plan.warnings:
        print(" WARNINGS:")
        for i, warning in enumerate(trip_plan.warnings[:3], 1):
            print(f"   {i}. {warning}")
        if len(trip_plan.warnings) > 3:
            print(f"   ... and {len(trip_plan.warnings) - 3} more")
        print()
    
    # ========================================
    # GENERATE PDF - CORRECT FILENAME
    # ========================================
    
    print_header(" GENERATING PDF")
    
    # CORRECT: Get string name, then lowercase it
    dest_name = trip_plan.destination.destination.name.lower().replace(" ", "_")
    start_date_str = trip_request.start_date.strftime("%Y%m%d")
    output_filename = f"outputs/{dest_name}_itinerary_{start_date_str}.pdf"
    
    print(f" Creating PDF: {output_filename}")
    print("   This may take a few seconds...")
    
    try:
        pdf_path = generate_trip_pdf(trip_plan, output_filename)
        
        file_size = os.path.getsize(pdf_path)
        file_size_kb = file_size / 1024
        
        print(f"\n PDF generated successfully!")
        print(f"    Location: {pdf_path}")
        print(f"    File size: {file_size_kb:.1f} KB")
        print(f"    Pages: ~{len(trip_plan.itinerary.days) * 2 + 4}")
        
    except Exception as e:
        print(f"\n Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # ========================================
    # DONE
    # ========================================
    
    print_header("🎉 COMPLETE")
    
    print("Your trip itinerary PDF is ready!")
    print()
    print(" What's included:")
    print("    Cover page")
    print("    Trip overview")
    print("    Flight details (from Amadeus API)")
    print("    Hotel information")
    print("    Day-by-day itinerary")
    print("    Restaurant guide")
    print("    Budget breakdown")
    print("    Important notes & tips")
    print()
    print(f" Open the PDF: {pdf_path}")
    print()
    
    # Optional: Open PDF automatically (macOS)
    try:
        import platform
        if platform.system() == 'Darwin':
            print(" Opening PDF...")
            os.system(f'open "{pdf_path}"')
    except:
        pass


if __name__ == "__main__":
    print("\n Starting PDF generation...\n")
    asyncio.run(main())
    print("\n Done! Thank you for using TripCraft.\n")