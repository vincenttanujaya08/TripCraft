"""
ResponseGenerator - Natural Language Response Generation

Converts action results into natural, helpful responses

Author: TripCraft Team  
Date: 2024
"""

import logging
from typing import Any, List, Dict
from backend.models.conversation_schemas import (
    ActionResult,
    ModificationResult,
    QueueResult,
    ProactiveSuggestion
)

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Generate natural language responses"""
    
    def __init__(self):
        logger.info("✅ ResponseGenerator initialized")
    
    def format_initial_plan_response(
        self,
        trip_plan: Any,
        image_loading: bool = True
    ) -> str:
        """Format response for initial plan creation"""
        
        try:
            dest_name = trip_plan.destination.destination.name
            days = len(trip_plan.itinerary.days)
            total_cost = trip_plan.budget.breakdown.total
            remaining = trip_plan.budget.breakdown.remaining
            hotel_name = trip_plan.hotels.recommended_hotel.name if trip_plan.hotels.recommended_hotel else "N/A"
            confidence = trip_plan.overall_confidence
            
            response = f"""✅ **Trip plan siap untuk {dest_name}!**

📊 **Summary:**
• Duration: {days} hari
• Total Cost: Rp {total_cost:,.0f}
• Budget Remaining: Rp {remaining:,.0f}
• Hotel: {hotel_name}
• Confidence: {confidence:.0%}
"""
            
            if image_loading:
                response += "\n🔄 Images sedang dimuat... (akan muncul sebentar lagi)\n"
            
            response += """
**Mau review detail atau ada yang ingin diganti?**

Contoh perintah:
• "Show hotel options" - Lihat pilihan hotel lain
• "Ganti hotel yang lebih murah" - Cari hotel lebih affordable
• "Day 2 lunch harus vegetarian" - Ubah makanan
• "Tambah beach activity" - Tambah aktivitas
• "Apply" - Terapkan perubahan yang pending

Ketik perintah Anda atau "help" untuk bantuan lengkap."""
            
            return response
            
        except Exception as e:
            logger.error(f"Error formatting initial plan response: {e}")
            return "✅ Trip plan created successfully! Type 'show plan' to view details."
    
    def format_modification_queued_response(
        self,
        result: QueueResult,
        queue_summary: List[str]
    ) -> str:
        """Format response for queued modification"""
        
        if not result.success:
            response = f"❌ **Tidak bisa diterapkan:**\n{result.message}\n"
            
            if result.suggestions:
                response += "\n**Saran:**\n"
                for i, suggestion in enumerate(result.suggestions, 1):
                    response += f"{i}. {suggestion}\n"
            
            return response
        
        response = f"✓ **{result.message}**\n\n"
        response += f"**Pending changes ({result.pending_count}):**\n"
        
        for i, item in enumerate(queue_summary, 1):
            response += f"{i}. {item}\n"
        
        response += "\n**Perintah selanjutnya:**\n"
        response += "• Tambah perubahan lain\n"
        response += "• Ketik **'apply'** untuk eksekusi semua\n"
        response += "• Ketik **'clear'** untuk batalkan semua\n"
        
        return response
    
    def format_modifications_applied_response(
        self,
        old_plan: Any,
        new_plan: Any,
        results: List[ModificationResult]
    ) -> str:
        """Format response for applied modifications"""
        
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        response = f"✅ **{len(successful)} perubahan berhasil diterapkan!**\n\n"
        
        # List changes
        response += "**Changes:**\n"
        for i, result in enumerate(successful, 1):
            response += f"{i}. {result.modification.description}\n"
        
        if failed:
            response += f"\n⚠️  **{len(failed)} perubahan gagal:**\n"
            for i, result in enumerate(failed, 1):
                response += f"{i}. {result.modification.description}: {result.errors[0]}\n"
        
        # Budget comparison
        try:
            old_total = old_plan.budget.breakdown.total
            new_total = new_plan.budget.breakdown.total
            diff = new_total - old_total
            
            response += "\n**Budget Update:**\n"
            response += f"• Before: Rp {old_total:,.0f}\n"
            response += f"• After: Rp {new_total:,.0f}\n"
            
            if diff < 0:
                response += f"• 💰 Hemat: Rp {abs(diff):,.0f}\n"
            elif diff > 0:
                response += f"• 📈 Tambah: Rp {diff:,.0f}\n"
            else:
                response += f"• ➡️  No change\n"
        except:
            pass
        
        response += "\n**Next steps:**\n"
        response += "• Ubah lagi? Langsung ketik perintah\n"
        response += "• Sudah final? Ketik **'finalize'**\n"
        response += "• Undo? Ketik **'undo'**\n"
        
        return response
    
    def format_query_response(self, query_type: str, data: Any) -> str:
        """Format response for query requests"""
        
        if query_type == "budget":
            return self._format_budget_query(data)
        
        elif query_type == "itinerary":
            return self._format_itinerary_query(data)
        
        elif query_type == "hotel":
            return self._format_hotel_query(data)
        
        elif query_type == "restaurants":
            return self._format_restaurant_query(data)
        
        return "Query processed successfully."
    
    def _format_budget_query(self, budget_output: Any) -> str:
        """Format budget information"""
        
        try:
            b = budget_output.breakdown
            
            response = "💰 **Budget Breakdown:**\n\n"
            response += f"• Flights: Rp {b.flights:,.0f}\n"
            response += f"• Accommodation: Rp {b.accommodation:,.0f}\n"
            response += f"• Food: Rp {b.food:,.0f}\n"
            response += f"• Activities: Rp {b.activities:,.0f}\n"
            response += f"• Local Transport: Rp {b.transportation_local:,.0f}\n"
            response += f"• Miscellaneous: Rp {b.miscellaneous:,.0f}\n"
            response += f"\n**Total:** Rp {b.total:,.0f}\n"
            response += f"**Remaining:** Rp {b.remaining:,.0f}\n"
            
            if budget_output.is_within_budget:
                response += "\n✅ Within budget!"
            else:
                response += "\n⚠️  Over budget!"
            
            return response
        except Exception as e:
            logger.error(f"Error formatting budget: {e}")
            return "Budget information unavailable."
    
    def _format_itinerary_query(self, itinerary_output: Any) -> str:
        """Format itinerary information"""
        
        try:
            response = "📅 **Day-by-Day Itinerary:**\n\n"
            
            for day in itinerary_output.days[:3]:  # Show first 3 days
                response += f"**Day {day.day_number} ({day.date}):**\n"
                
                for activity in day.activities[:3]:  # Show first 3 activities
                    response += f"  • {activity.time}: {activity.name}\n"
                
                if len(day.activities) > 3:
                    response += f"  ... and {len(day.activities) - 3} more activities\n"
                
                response += "\n"
            
            if len(itinerary_output.days) > 3:
                response += f"... and {len(itinerary_output.days) - 3} more days\n"
            
            response += "\nKetik 'show full itinerary' untuk detail lengkap."
            
            return response
        except Exception as e:
            logger.error(f"Error formatting itinerary: {e}")
            return "Itinerary information unavailable."
    
    def _format_hotel_query(self, hotel_output: Any) -> str:
        """Format hotel information"""
        
        try:
            hotel = hotel_output.recommended_hotel
            
            response = f"🏨 **Recommended Hotel:**\n\n"
            response += f"**{hotel.name}**\n"
            response += f"• Type: {hotel.type}\n"
            response += f"• Rating: {'⭐' * int(hotel.rating or 0)} {hotel.rating}/5\n"
            response += f"• Price: Rp {hotel.price_per_night:,.0f}/night\n"
            response += f"• Location: {hotel.address or 'N/A'}\n"
            
            if hotel.amenities:
                response += f"• Amenities: {', '.join(hotel.amenities[:5])}\n"
            
            response += f"\n**Total Cost:** Rp {hotel_output.total_accommodation_cost:,.0f}\n"
            
            response += "\nMau lihat pilihan lain? Ketik 'show hotel options'"
            
            return response
        except Exception as e:
            logger.error(f"Error formatting hotel: {e}")
            return "Hotel information unavailable."
    
    def _format_restaurant_query(self, dining_output: Any) -> str:
        """Format restaurant information"""
        
        try:
            response = "🍽️  **Restaurant Recommendations:**\n\n"
            
            for i, restaurant in enumerate(dining_output.restaurants[:5], 1):
                response += f"**{i}. {restaurant.name}**\n"
                response += f"   • Cuisine: {restaurant.cuisine}\n"
                response += f"   • Price: Rp {restaurant.average_cost_per_person:,.0f}/person\n"
                response += f"   • Rating: {'⭐' * int(restaurant.rating or 0)}\n\n"
            
            if len(dining_output.restaurants) > 5:
                response += f"... and {len(dining_output.restaurants) - 5} more restaurants\n"
            
            return response
        except Exception as e:
            logger.error(f"Error formatting restaurants: {e}")
            return "Restaurant information unavailable."
    
    def format_proactive_suggestion(
        self,
        suggestion: ProactiveSuggestion
    ) -> str:
        """Format proactive suggestion"""
        
        icon = "💡" if suggestion.priority == "low" else "⚠️" if suggestion.priority == "medium" else "🚨"
        
        response = f"{icon} **Suggestion:**\n{suggestion.message}\n"
        
        if suggestion.estimated_impact:
            response += f"\n**Impact:** {suggestion.estimated_impact}\n"
        
        if suggestion.actions:
            response += "\n**Recommended actions:**\n"
            for i, action in enumerate(suggestion.actions, 1):
                response += f"{i}. {action}\n"
        
        return response
    
    def format_error_response(self, error: str) -> str:
        """Format error message"""
        
        return f"""❌ **Error:**
{error}

**Butuh bantuan?**
Ketik 'help' untuk melihat perintah yang tersedia."""
    
    def format_help_response(self) -> str:
        """Format help message"""
        
        return """📖 **TripCraft Conversational Planner - Help**

**Planning:**
• "Plan trip to Bali for 5 days" - Mulai perencanaan
• "Budget 15 million rupiah" - Set budget

**Modifications:**
• "Change hotel to cheaper option" - Ganti hotel
• "Day 2 lunch must be vegetarian" - Ubah makanan
• "Add beach activity on Day 3" - Tambah aktivitas
• "Remove museum" - Hapus aktivitas

**Queries:**
• "Show budget" - Lihat breakdown budget
• "Show itinerary" - Lihat jadwal
• "Show hotel options" - Lihat pilihan hotel

**Actions:**
• "Apply" - Terapkan perubahan pending
• "Undo" - Batalkan perubahan terakhir
• "Finalize" - Selesaikan dan export
• "Clear" - Hapus semua pending changes

**Tips:**
• Anda bisa menambah beberapa perubahan sekaligus sebelum apply
• Semua perubahan bisa di-undo
• Ketik natural language, sistem akan memahami intent Anda

Butuh bantuan spesifik? Tanya saja! 😊"""
    
    def format_unclear_intent_response(self, message: str) -> str:
        """Format response when intent is unclear"""
        
        return f"""🤔 Maaf, saya kurang paham maksud Anda: "{message}"

**Apakah Anda ingin:**
1. Merencanakan trip baru? (Ketik: "Plan trip to [destination]")
2. Mengubah sesuatu? (Ketik: "Change [hotel/meal/activity]")
3. Melihat informasi? (Ketik: "Show [budget/itinerary/hotels]")

Atau ketik **'help'** untuk melihat contoh perintah."""


# Singleton instance
_response_generator = None

def get_response_generator() -> ResponseGenerator:
    """Get singleton ResponseGenerator instance"""
    global _response_generator
    if _response_generator is None:
        _response_generator = ResponseGenerator()
    return _response_generator