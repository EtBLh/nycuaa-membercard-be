import os
from PyPDF2 import PdfReader, PdfWriter

def split_pdf(input_pdf):
    # Create a directory named 'invoice' if it doesn't exist
    if not os.path.exists('invoice'):
        os.makedirs('invoice')

    # Open the input PDF file
    with open(input_pdf, 'rb') as file:
        pdf_reader = PdfReader(file)
        num_pages = len(pdf_reader.pages)

        # Loop through each page and create a separate PDF for each
        for page_num in range(num_pages):
            pdf_writer = PdfWriter()
            pdf_writer.add_page(pdf_reader.pages[page_num])

            # Define the output file path
            output_filename = f'invoice/{page_num + 1}.pdf'

            # Write the single page to a new PDF file
            with open(output_filename, 'wb') as output_file:
                pdf_writer.write(output_file)

            print(f'Created: {output_filename}')

# Replace 'your_file.pdf' with the path to your input PDF file
split_pdf('invoice.pdf')
