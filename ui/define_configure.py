import streamlit as st
import models
from . import manage_lookups, metrics

def show_define_and_configure():
    """Show the configuration page with options to manage lookups and metrics"""
    
    # Get data for selection
    cats = models.get_categories()
    units = models.get_units()
    
    # Manage lookups (categories and units)
    manage_lookups.show_manage_lookups()
    
    # Create metrics
    metrics.show_create_metric(cats, units)
