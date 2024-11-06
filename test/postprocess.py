import subprocess
import json
import os

directories = [
    # "/store/user/chpapage/SUEPNano_Jul2024/QCD_Pt-1000_MuEnrichedPt5_TuneCP5_13TeV-pythia8/QCD_Pt-1000_MuEnrichedPt5/240716_141538/0000",
    "/store/user/chpapage/SUEPNano_Jul2024/QCD_Pt-120To170_MuEnrichedPt5_TuneCP5_13TeV-pythia8/QCD_Pt-120To170_MuEnrichedPt5/240716_141602/0000",
    "/store/user/chpapage/SUEPNano_Jul2024/QCD_Pt-15To20_MuEnrichedPt5_TuneCP5_13TeV-pythia8/QCD_Pt-15To20_MuEnrichedPt5/240716_141525/0000",
    "/store/user/chpapage/SUEPNano_Jul2024/QCD_Pt-170To300_MuEnrichedPt5_TuneCP5_13TeV-pythia8/QCD_Pt-170To300_MuEnrichedPt5/240716_141357/0000",
    "/store/user/chpapage/SUEPNano_Jul2024/QCD_Pt-20To30_MuEnrichedPt5_TuneCP5_13TeV-pythia8/QCD_Pt-20To30_MuEnrichedPt5/240716_141458/0000",
    "/store/user/chpapage/SUEPNano_Jul2024/QCD_Pt-300To470_MuEnrichedPt5_TuneCP5_13TeV-pythia8/QCD_Pt-300To470_MuEnrichedPt5/240716_141421/0000",
    "/store/user/chpapage/SUEPNano_Jul2024/QCD_Pt-30To50_MuEnrichedPt5_TuneCP5_13TeV-pythia8/QCD_Pt-30To50_MuEnrichedPt5/240716_141434/0000",
    "/store/user/chpapage/SUEPNano_Jul2024/QCD_Pt-470To600_MuEnrichedPt5_TuneCP5_13TeV-pythia8/QCD_Pt-470To600_MuEnrichedPt5/240716_141342/0000",
    "/store/user/chpapage/SUEPNano_Jul2024/QCD_Pt-50To80_MuEnrichedPt5_TuneCP5_13TeV-pythia8/QCD_Pt-50To80_MuEnrichedPt5/240716_141511/0000",
    "/store/user/chpapage/SUEPNano_Jul2024/QCD_Pt-600To800_MuEnrichedPt5_TuneCP5_13TeV-pythia8/QCD_Pt-600To800_MuEnrichedPt5/240716_141447/0000",
    "/store/user/chpapage/SUEPNano_Jul2024/QCD_Pt-800To1000_MuEnrichedPt5_TuneCP5_13TeV-pythia8/QCD_Pt-800To1000_MuEnrichedPt5/240716_141409/0000",
    "/store/user/chpapage/SUEPNano_Jul2024/QCD_Pt-80To120_MuEnrichedPt5_TuneCP5_13TeV-pythia8/QCD_Pt-80To120_MuEnrichedPt5/240716_141550/0000",
]
eos_redirector = "root://cmseos.fnal.gov/"
output_base_dir = "/store/user/chpapage/SUEPNano_Jul2024_merged"
max_size = 1 * 1024 * 1024 * 1024  # 1GB

def eos_ls(directory):
    command = "source ~/.bash_profile 2>/dev/null; eos {} ls {}".format(eos_redirector, directory)
    result = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, executable='/bin/bash')
    out, err = result.communicate()
    return out.decode('utf-8').strip().split('\n')

def eos_file_size(file_path):
    command = "source ~/.bash_profile 2>/dev/null; eos {} stat {}".format(eos_redirector, file_path)
    result = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, executable='/bin/bash')
    out, err = result.communicate()
    next_one = False
    for item in out.decode('utf-8').strip().split(' '):
        if next_one:
            return int(item)
        if item == 'Size:':
            next_one = True
        

def merge_files(file_list, output_file):
    command = ["python", "haddnano.py"] + ["temp.root"] + ["root://cmseos.fnal.gov/" + f_i for f_i in file_list]
    subprocess.check_call(command)
    command = ["xrdcp", "temp.root", "root://cmseos.fnal.gov/" + output_file]
    subprocess.check_call(command)
    os.remove("temp.root")

def process_directory(directory):
    subdir = directory.split('/')[-4]  # Adjusting to get the correct subdir name for JSON
    json_data = {}
    files = eos_ls(directory)

    if not files:
        return json_data

    file_list = [os.path.join(directory, file) for file in files if file.endswith(".root")]
    merged_files = []
    temp_files = []
    temp_size = 0
    file_index = 1

    for file in file_list:
        size = eos_file_size(file)
        if temp_size + size > max_size:
            output_file = os.path.join(output_base_dir, "{}/skim_{}.root".format(subdir, file_index))
            merge_files(temp_files, output_file)
            merged_files.append(output_file)
            temp_files = []
            temp_size = 0
            file_index += 1

        temp_files.append(file)
        temp_size += size

    if temp_files:
        output_file = os.path.join(output_base_dir, "{}/skim_{}.root".format(subdir, file_index))
        merge_files(temp_files, output_file)
        merged_files.append(output_file)

    json_data[subdir] = ["root://cmseos.fnal.gov//{}".format(output_file) for output_file in merged_files]

    return json_data

def main():
    all_data = {}
    for directory in directories:
        data = process_directory(directory)
        all_data.update(data)

    json_output = "merged_files.json"
    with open(json_output, 'w') as json_file:
        json.dump(all_data, json_file, indent=4)

    print("JSON file created: {}".format(json_output))

if __name__ == "__main__":
    main()
