README - Logo Similarity

I've started by separating the logic of the problem in two parts. The first part
consists of building the domain's url and than downloading the logo. The second
part groups the logo based on similarity.

I start by checking if the domain exists on the Internet. Basically, it asks the
OS if the domain exists, the OS than asks a domain name system if it exists. If
it exists, it sends the IP back. After this, I build the URL. I try protocols,
like http, https and subdomains, like www., www2. etc. Using scrapper, I send
a HTTP request to see the access. The next part is to download the logo. If the
file already exists, it returns it. Otherwise, it downloads the HTML and then 
search for all img. The thing is that, the first image found is not chosen as 
the logo, but scored. Also, it searches the meta tags. Then, sort the scores,
and the winner is the one with the biggest score, that's the logo. Build the 
path and download it. Just in case, I check the javascript in search for the 
logo. It starts a phantom browser, waits for the java to be executed, and scans
the interface searching for the logo. The system score is the same as previously.
(this has a lock, because I work with threads to process the domains faster, and
starting the browser with multiple threads will turn into a deadlock). These
steps are called in a seperate function. I collect data, how many sites where
accessed, how many were unaccessible, how many logos were downloaded.

Now comes the part for the similarity. The first step is to take the picture 
(JPG, PNG) and transforms it into a standard object (RGB) on white background,
so that the algorithm is not tricked by transperency or different shapes. So, 
from the image, it turns it into a matrix of numbers which the algorithm can 
measure and see if the logos are similar. And the solution of the problem is
to calculate a hash which is unic and then compare the hashes. If the 
difference between hashes is small, then they are similar. I compare the hashes
using the hamming distance and group the logos based on that. The is calculated
as it follows: resizes the image into a small square, eliminates the colors, 
leaving only the lights, apply discrete cosine transform to turn from pixels
to frequencies (separates the sections where the image changes fast and slow),
reduces the frequency, keeping the left corner from the upside, because the 
lowest frequencies are located there, calculates the average and generate the
bit.

I have used this solution because is fast, less RAM used. It is fast because
I used parallel work, and for the RAM, the use of playwright is a fallback.
The ideea came from seeing white as predominant in pictures, and also because
recently I have learned about lights, how they work, and how they help me in
the similarity problem.

The problem with this solution is that I don't think is as accurate as a ML
algorithm using clustering, CNN, OCR.
