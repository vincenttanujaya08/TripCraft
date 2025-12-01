"""
Professional PDF Itinerary Generator
FULLY CORRECTED: All attributes match exact Pydantic schemas

Flight: departure_airport, arrival_airport (NOT origin/destination)
Restaurant: average_cost_per_person, address (NOT price/location)
DailyMealPlan: daily_cost (NOT total_cost)
DestinationInfo: name, country (accessed via .destination.name)
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from datetime import datetime
import os


class PDFItineraryGenerator:
    """Generate professional PDF itineraries"""
    
    COLOR_PRIMARY = colors.HexColor('#1E40AF')
    COLOR_SECONDARY = colors.HexColor('#3B82F6')
    COLOR_TEXT = colors.HexColor('#1F2937')
    COLOR_GRAY = colors.HexColor('#6B7280')
    COLOR_LIGHT_GRAY = colors.HexColor('#F3F4F6')
    COLOR_WARNING = colors.HexColor('#F59E0B')
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
    
    def _create_custom_styles(self):
        """Create custom paragraph styles"""
        
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=28,
            textColor=self.COLOR_PRIMARY,
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Normal'],
            fontSize=16,
            textColor=self.COLOR_SECONDARY,
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=self.COLOR_PRIMARY,
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='SubsectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=self.COLOR_SECONDARY,
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=self.COLOR_TEXT,
            spaceAfter=8,
            leading=14,
            fontName='Helvetica'
        ))
        
        self.styles.add(ParagraphStyle(
            name='SmallText',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=self.COLOR_GRAY,
            spaceAfter=6,
            fontName='Helvetica'
        ))
        
        self.styles.add(ParagraphStyle(
            name='Warning',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.COLOR_WARNING,
            spaceAfter=8,
            fontName='Helvetica-Bold'
        ))
    
    def generate_itinerary(self, trip_plan, output_path: str):
        """Generate complete trip itinerary PDF"""
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2.5*cm,
            bottomMargin=2*cm
        )
        
        story = []
        story.extend(self._create_cover_page(trip_plan))
        story.extend(self._create_overview(trip_plan))
        story.extend(self._create_flight_details(trip_plan))
        story.extend(self._create_hotel_details(trip_plan))
        story.extend(self._create_daily_itinerary(trip_plan))
        story.extend(self._create_restaurant_guide(trip_plan))
        story.extend(self._create_budget_breakdown(trip_plan))
        story.extend(self._create_important_notes(trip_plan))
        
        doc.build(story, onFirstPage=self._add_page_decorations,
                  onLaterPages=self._add_page_decorations)
        
        return output_path
    
    def _create_cover_page(self, trip_plan):
        """Create cover page"""
        elements = []
        
        elements.append(Spacer(1, 2*inch))
        
        icon = Paragraph("🌍", self.styles['CustomTitle'])
        elements.append(icon)
        
        title = Paragraph("TRIP ITINERARY", self.styles['CustomTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        # CORRECT: destination is DestinationInfo with .name
        dest_name = trip_plan.destination.destination.name
        destination = Paragraph(f"<b>{dest_name}</b>", self.styles['CustomSubtitle'])
        elements.append(destination)
        elements.append(Spacer(1, 0.2*inch))
        
        # Dates
        try:
            start_date = trip_plan.itinerary.days[0].date
            end_date = trip_plan.itinerary.days[-1].date
            dates = Paragraph(f"{start_date} - {end_date}", self.styles['CustomBody'])
        except:
            dates = Paragraph("Date information unavailable", self.styles['CustomBody'])
        
        elements.append(dates)
        elements.append(Spacer(1, 1*inch))
        
        generated = Paragraph(
            f"Generated by TripCraft AI<br/>{datetime.now().strftime('%d %B %Y')}",
            self.styles['SmallText']
        )
        elements.append(generated)
        elements.append(PageBreak())
        
        return elements
    
    def _create_overview(self, trip_plan):
        """Create trip overview section"""
        elements = []
        
        header = Paragraph("📋 TRIP OVERVIEW", self.styles['SectionHeader'])
        elements.append(header)
        elements.append(Spacer(1, 0.2*inch))
        
        duration_days = len(trip_plan.itinerary.days)
        
        data = [
            ["Destination", trip_plan.destination.destination.name],
            ["Duration", f"{duration_days} days ({duration_days - 1} nights)"],
            ["Total Budget", f"Rp {trip_plan.budget.breakdown.total + trip_plan.budget.breakdown.remaining:,.0f}"],
            ["Total Cost", f"Rp {trip_plan.budget.breakdown.total:,.0f}"],
            ["Remaining", f"Rp {trip_plan.budget.breakdown.remaining:,.0f} {'✓' if trip_plan.budget.is_within_budget else '✗'}"],
        ]
        
        table = Table(data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), self.COLOR_LIGHT_GRAY),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.COLOR_TEXT),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, self.COLOR_GRAY),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _create_flight_details(self, trip_plan):
        """Create flight details section"""
        elements = []
        
        header = Paragraph("✈️ FLIGHT DETAILS", self.styles['SectionHeader'])
        elements.append(header)
        elements.append(Spacer(1, 0.2*inch))
        
        # Outbound - CORRECT: departure_airport, arrival_airport
        if trip_plan.flights.recommended_outbound:
            flight = trip_plan.flights.recommended_outbound
            
            outbound = Paragraph("🛫 OUTBOUND FLIGHT", self.styles['SubsectionHeader'])
            elements.append(outbound)
            
            flight_data = [
                ["Airline", f"{flight.airline} ({flight.flight_number})"],
                ["Route", f"{flight.departure_airport} → {flight.arrival_airport}"],
                ["Departure", str(flight.departure_time)],
                ["Arrival", str(flight.arrival_time)],
                ["Duration", f"{flight.duration_hours:.1f} hours"],
                ["Price", f"Rp {flight.price:,.0f}/person"],
            ]
            
            table = Table(flight_data, colWidths=[1.5*inch, 4.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), self.COLOR_LIGHT_GRAY),
                ('TEXTCOLOR', (0, 0), (-1, -1), self.COLOR_TEXT),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, self.COLOR_GRAY),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 0.2*inch))
        
        # Return flight
        if trip_plan.flights.recommended_return:
            flight = trip_plan.flights.recommended_return
            
            return_header = Paragraph("🛬 RETURN FLIGHT", self.styles['SubsectionHeader'])
            elements.append(return_header)
            
            flight_data = [
                ["Airline", f"{flight.airline} ({flight.flight_number})"],
                ["Route", f"{flight.departure_airport} → {flight.arrival_airport}"],
                ["Departure", str(flight.departure_time)],
                ["Arrival", str(flight.arrival_time)],
                ["Duration", f"{flight.duration_hours:.1f} hours"],
                ["Price", f"Rp {flight.price:,.0f}/person"],
            ]
            
            table = Table(flight_data, colWidths=[1.5*inch, 4.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), self.COLOR_LIGHT_GRAY),
                ('TEXTCOLOR', (0, 0), (-1, -1), self.COLOR_TEXT),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, self.COLOR_GRAY),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 0.2*inch))
        
        # Total cost
        total_cost = Paragraph(
            f"<b>Total Flight Cost:</b> Rp {trip_plan.flights.total_flight_cost:,.0f}",
            self.styles['CustomBody']
        )
        elements.append(total_cost)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _create_hotel_details(self, trip_plan):
        """Create hotel details section"""
        elements = []
        
        header = Paragraph("🏨 ACCOMMODATION", self.styles['SectionHeader'])
        elements.append(header)
        elements.append(Spacer(1, 0.2*inch))
        
        if not trip_plan.hotels.recommended_hotel:
            elements.append(Paragraph("No hotel information available", self.styles['CustomBody']))
            return elements
        
        hotel = trip_plan.hotels.recommended_hotel
        
        stars = "⭐" * int(hotel.rating) if hotel.rating else ""
        hotel_data = [
            ["Hotel", f"{hotel.name} {stars}"],
            ["Rating", f"{hotel.rating}/5" if hotel.rating else "N/A"],
            ["Location", hotel.address or "Not specified"],
            ["Nights", f"{len(trip_plan.itinerary.days) - 1}"],
            ["Price/night", f"Rp {hotel.price_per_night:,.0f}"],
        ]
        
        if hotel.amenities:
            hotel_data.append(["Amenities", ", ".join(hotel.amenities[:5])])
        
        table = Table(hotel_data, colWidths=[1.5*inch, 4.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), self.COLOR_LIGHT_GRAY),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.COLOR_TEXT),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, self.COLOR_GRAY),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))
        
        total_cost = Paragraph(
            f"<b>Total Hotel Cost:</b> Rp {trip_plan.hotels.total_accommodation_cost:,.0f}",
            self.styles['CustomBody']
        )
        elements.append(total_cost)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _create_daily_itinerary(self, trip_plan):
        """Create day-by-day itinerary"""
        elements = []
        
        header = Paragraph("📅 DAY-BY-DAY ITINERARY", self.styles['SectionHeader'])
        elements.append(header)
        elements.append(Spacer(1, 0.2*inch))
        
        for day_num, day_itinerary in enumerate(trip_plan.itinerary.days, 1):
            # Day header
            day_title = f"DAY {day_num} - {day_itinerary.date}"
            day_header = Paragraph(day_title, self.styles['SubsectionHeader'])
            elements.append(day_header)
            elements.append(Spacer(1, 0.1*inch))
            
            # Get meals for this day
            meal_items = []
            try:
                day_meals = trip_plan.dining.meal_plan[day_num - 1]
                
                if day_meals.breakfast:
                    # CORRECT: average_cost_per_person, not price
                    meal_items.append([
                        "🍳 Breakfast",
                        f"{day_meals.breakfast.name}<br/>"
                        f"<font size=9 color='#{self.COLOR_GRAY.hexval()[2:]}'>"
                        f"Rp {day_meals.breakfast.average_cost_per_person:,.0f}/person</font>"
                    ])
                
                if day_meals.lunch:
                    meal_items.append([
                        "🍽️ Lunch",
                        f"{day_meals.lunch.name}<br/>"
                        f"<font size=9 color='#{self.COLOR_GRAY.hexval()[2:]}'>"
                        f"{day_meals.lunch.cuisine} • Rp {day_meals.lunch.average_cost_per_person:,.0f}/person</font>"
                    ])
                
                if day_meals.dinner:
                    meal_items.append([
                        "🍷 Dinner",
                        f"{day_meals.dinner.name}<br/>"
                        f"<font size=9 color='#{self.COLOR_GRAY.hexval()[2:]}'>"
                        f"{day_meals.dinner.cuisine} • Rp {day_meals.dinner.average_cost_per_person:,.0f}/person</font>"
                    ])
            except:
                pass
            
            if meal_items:
                meal_table = Table(meal_items, colWidths=[1.2*inch, 4.8*inch])
                meal_table.setStyle(TableStyle([
                    ('TEXTCOLOR', (0, 0), (-1, -1), self.COLOR_TEXT),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                ]))
                elements.append(meal_table)
                elements.append(Spacer(1, 0.1*inch))
            
            # Activities
            if day_itinerary.activities:
                activity_header = Paragraph("📍 ACTIVITIES", self.styles['CustomBody'])
                elements.append(activity_header)
                
                for i, activity in enumerate(day_itinerary.activities, 1):
                    activity_text = f"<b>{i}. {activity.name}</b>"
                    if activity.time:
                        activity_text += f" ({activity.time})"
                    activity_text += f"<br/>{activity.description}"
                    
                    activity_para = Paragraph(activity_text, self.styles['CustomBody'])
                    elements.append(activity_para)
                    elements.append(Spacer(1, 0.05*inch))
            
            # Day total - CORRECT: daily_cost not total_cost
            try:
                day_meals = trip_plan.dining.meal_plan[day_num - 1]
                total_para = Paragraph(
                    f"<b>Day {day_num} Total:</b> Rp {day_meals.daily_cost:,.0f}",
                    self.styles['CustomBody']
                )
                elements.append(total_para)
            except:
                pass
            
            elements.append(Spacer(1, 0.3*inch))
            
            if day_num % 2 == 0 and day_num < len(trip_plan.itinerary.days):
                elements.append(PageBreak())
        
        return elements
    
    def _create_restaurant_guide(self, trip_plan):
        """Create restaurant guide"""
        elements = []
        
        header = Paragraph("🍽️ RESTAURANT GUIDE", self.styles['SectionHeader'])
        elements.append(header)
        elements.append(Spacer(1, 0.2*inch))
        
        intro = Paragraph("All restaurants included in this itinerary:", self.styles['CustomBody'])
        elements.append(intro)
        elements.append(Spacer(1, 0.1*inch))
        
        # Collect unique restaurants
        restaurants = set()
        for day_meals in trip_plan.dining.meal_plan:
            if day_meals.breakfast and day_meals.breakfast.name != "Hotel breakfast":
                restaurants.add((
                    day_meals.breakfast.name,
                    day_meals.breakfast.cuisine,
                    day_meals.breakfast.average_cost_per_person,
                    day_meals.breakfast.address or "Location not specified"
                ))
            if day_meals.lunch:
                restaurants.add((
                    day_meals.lunch.name,
                    day_meals.lunch.cuisine,
                    day_meals.lunch.average_cost_per_person,
                    day_meals.lunch.address or "Location not specified"
                ))
            if day_meals.dinner:
                restaurants.add((
                    day_meals.dinner.name,
                    day_meals.dinner.cuisine,
                    day_meals.dinner.average_cost_per_person,
                    day_meals.dinner.address or "Location not specified"
                ))
        
        for i, (name, cuisine, price, address) in enumerate(sorted(restaurants), 1):
            restaurant_text = (
                f"<b>{i}. {name}</b><br/>"
                f"<font size=9 color='#{self.COLOR_GRAY.hexval()[2:]}'>"
                f"{cuisine} • Rp {price:,.0f}/person<br/>"
                f"{address}</font>"
            )
            restaurant_para = Paragraph(restaurant_text, self.styles['CustomBody'])
            elements.append(restaurant_para)
            elements.append(Spacer(1, 0.1*inch))
        
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _create_budget_breakdown(self, trip_plan):
        """Create budget breakdown"""
        elements = []
        
        header = Paragraph("💰 BUDGET BREAKDOWN", self.styles['SectionHeader'])
        elements.append(header)
        elements.append(Spacer(1, 0.2*inch))
        
        total = trip_plan.budget.breakdown.total
        
        budget_data = [
            ["Category", "Amount", "Percentage"],
            ["Flights", f"Rp {trip_plan.budget.breakdown.flights:,.0f}", 
             f"{(trip_plan.budget.breakdown.flights/total*100):.1f}%"],
            ["Accommodation", f"Rp {trip_plan.budget.breakdown.accommodation:,.0f}",
             f"{(trip_plan.budget.breakdown.accommodation/total*100):.1f}%"],
            ["Food & Dining", f"Rp {trip_plan.budget.breakdown.food:,.0f}",
             f"{(trip_plan.budget.breakdown.food/total*100):.1f}%"],
            ["Activities", f"Rp {trip_plan.budget.breakdown.activities:,.0f}",
             f"{(trip_plan.budget.breakdown.activities/total*100):.1f}%"],
            ["Local Transport", f"Rp {trip_plan.budget.breakdown.transportation_local:,.0f}",
             f"{(trip_plan.budget.breakdown.transportation_local/total*100):.1f}%"],
            ["Miscellaneous", f"Rp {trip_plan.budget.breakdown.miscellaneous:,.0f}",
             f"{(trip_plan.budget.breakdown.miscellaneous/total*100):.1f}%"],
        ]
        
        table = Table(budget_data, colWidths=[2.5*inch, 2*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, self.COLOR_GRAY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.COLOR_LIGHT_GRAY]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Total summary
        total_budget = total + trip_plan.budget.breakdown.remaining
        summary_data = [
            ["TOTAL COST", f"Rp {total:,.0f}"],
            ["BUDGET", f"Rp {total_budget:,.0f}"],
            ["REMAINING", f"Rp {trip_plan.budget.breakdown.remaining:,.0f}"],
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5*inch, 3.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.COLOR_LIGHT_GRAY),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.COLOR_TEXT),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('LINEABOVE', (0, 0), (-1, 0), 2, self.COLOR_PRIMARY),
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _create_important_notes(self, trip_plan):
        """Create important notes section"""
        elements = []
        
        header = Paragraph("📌 IMPORTANT NOTES", self.styles['SectionHeader'])
        elements.append(header)
        elements.append(Spacer(1, 0.2*inch))
        
        # Warnings
        if trip_plan.warnings:
            warning_header = Paragraph("⚠️ Warnings:", self.styles['SubsectionHeader'])
            elements.append(warning_header)
            
            for warning in trip_plan.warnings[:5]:
                warning_text = f"• {warning}"
                warning_para = Paragraph(warning_text, self.styles['Warning'])
                elements.append(warning_para)
            
            elements.append(Spacer(1, 0.2*inch))
        
        # General tips
        tips_header = Paragraph("✅ Tips:", self.styles['SubsectionHeader'])
        elements.append(tips_header)
        
        tips = [
            f"Best time to visit: {trip_plan.destination.destination.best_time_to_visit}",
            f"Local currency: {trip_plan.destination.destination.local_currency}",
            f"Timezone: {trip_plan.destination.destination.timezone}",
            f"Language: {trip_plan.destination.destination.language}",
        ]
        
        for tip in tips:
            tip_para = Paragraph(f"• {tip}", self.styles['CustomBody'])
            elements.append(tip_para)
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Footer info
        footer_text = (
            f"Generated by TripCraft AI<br/>"
            f"Date: {datetime.now().strftime('%d %B %Y')}<br/>"
            f"Trip Confidence: {trip_plan.overall_confidence:.2%}"
        )
        footer = Paragraph(footer_text, self.styles['SmallText'])
        elements.append(footer)
        
        return elements
    
    def _add_page_decorations(self, canvas, doc):
        """Add header and footer to each page"""
        canvas.saveState()
        
        # Header line
        canvas.setStrokeColor(self.COLOR_PRIMARY)
        canvas.setLineWidth(2)
        canvas.line(2*cm, A4[1] - 2*cm, A4[0] - 2*cm, A4[1] - 2*cm)
        
        # Footer
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(self.COLOR_GRAY)
        canvas.drawString(2*cm, 1.5*cm, f"TripCraft AI • Page {doc.page}")
        canvas.drawRightString(A4[0] - 2*cm, 1.5*cm, datetime.now().strftime('%d %B %Y'))
        
        canvas.restoreState()


def generate_trip_pdf(trip_plan, output_path: str = "outputs/trip_itinerary.pdf"):
    """Convenience function to generate PDF"""
    generator = PDFItineraryGenerator()
    return generator.generate_itinerary(trip_plan, output_path)