#!/bin/bash

# Rivian Analysis Project Setup Script

echo "========================================"
echo "Rivian Analysis Environment Setup"
echo "========================================"
echo ""

# Check if conda is installed
if ! command -v conda &> /dev/null
then
    echo "ERROR: conda is not installed. Please install Anaconda or Miniconda first."
    echo "Visit: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

echo "✓ Conda detected"
echo ""

# Create conda environment
echo "Creating conda environment 'rivian_analysis'..."
conda env create -f environment.yml

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Environment created successfully!"
    echo ""
    echo "========================================"
    echo "Setup Complete!"
    echo "========================================"
    echo ""
    echo "To activate the environment, run:"
    echo "  conda activate rivian_analysis"
    echo ""
    echo "Then you can start using the ingestion pipeline:"
    echo "  python src/ingest.py"
    echo ""
else
    echo ""
    echo "✗ Error creating environment."
    echo "If the environment already exists, you can update it with:"
    echo "  conda env update -f environment.yml"
    exit 1
fi

