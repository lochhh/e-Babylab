(target-instrument-administration)=
# Instrument Administration

e-Babylab provides the option to administer adaptive, short-form versions of the MacArthur–Bates Communicative Development Inventories (CDIs) as a part of each experiment. CDIs (termed _Instruments_ in e-Babylab) are administered via item response theory and CDI estimates are computed based on prior CDI data (retrieved from [Wordbank](http://wordbank.stanford.edu/)) from children with matching key demographics ([Chai et al., 2020](https://doi.org/10.1044/2020_JSLHR-20-00361); [Mayor & Mani, 2019](https://doi.org/10.3758/s13428-018-1146-0)).

The CDI instruments a user has access to (i.e., has permission to change or delete) are shown in the Instrument Admin.

:::{figure} https://github.com/user-attachments/assets/ba265860-ffec-4c41-8e4e-d78857c012fe
:alt: Instrument Admin

Instrument Admin
:::

To add an Instrument, a user will need to:

1. Download the R script provided.
2. Edit `lang` (language), `type` (CDI type: WS or WG), and `resp` (comprehension or production) in the R script accordingly.
3. Run the R script to generate the required data files.
4. Upload the data files to e-Babylab.
5. Specify the location for each file in the Add Instrument form.

:::{figure} https://github.com/user-attachments/assets/3cee9f00-117f-4d74-9c79-9924205571bd
:alt: Add Instrument form

Add Instrument form
:::
