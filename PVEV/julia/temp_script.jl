
    using CSV
    using DataFrames

    include(raw"""urdb.jl""")
    include(raw"""electric_tariff.jl""")
    include(raw"""utils.jl""")
    using CSV
    # Load the CSV file
    function process_urdb_data(urdb_label, year=2025, time_steps_per_hour=1)
        # usurdb_data = CSV.read(raw"""C:\\Users\\jiahuic\\University of Michigan Dropbox\\Jiahui Chen\\PVEV\\julia\\filtered_usurdb_2023later.csv""", DataFrame)
        usurdb_data = CSV.read(raw"""E:\\University of Michigan Dropbox\\Jiahui Chen\\PVEV\\julia\\filtered_usurdb_2023later.csv""", DataFrame)

        # Find the 'utility' corresponding to the 'urdb_label'
        utility = usurdb_data[usurdb_data.label .== urdb_label, :utility][1]
        name = usurdb_data[usurdb_data.label .== urdb_label, :name][1]

        # Download and parse URDB data
        urdb_response = download_urdb(urdb_label)
        rate = URDBrate(urdb_response, year; time_steps_per_hour=time_steps_per_hour)

        # Extract energy_rates and fixed_monthly_charge
        energy_rates = vec(rate.energy_rates[:, 1])  # Ensure energy_rates is a 1D array
        fixed_monthly_charge = rate.fixed_monthly_charge
        # Determine if energy rates vary within the first 48 elements
        tou = any(diff(energy_rates[1:48]) .!= 0) ? '1' : '0'

        # Create a DataFrame
        df = DataFrame(energy_rates=energy_rates[:, 1], fixed_monthly_charge=fill(fixed_monthly_charge, length(energy_rates)), tou=fill(tou, length(energy_rates)))
        # Write to CSV with 'name' in the file name
        file_name = "E:\\University of Michigan Dropbox\\Jiahui Chen\\PVEV\\julia\\Utility_structure\\$(urdb_label).csv"
        # file_name = "C:\\Users\\jiahuic\\University of Michigan Dropbox\\Jiahui Chen\\PVEV\\julia\\Utility_structure\\$(urdb_label).csv"
        CSV.write(file_name, df)
    end
    process_urdb_data(raw"""668479c17ba7fc0e710f9f2d""")


    